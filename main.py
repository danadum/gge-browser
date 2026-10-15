"""
EN: Entry point. Launches Chrome, connects the CDP relay, starts the HTTP
    bridge, and lets the user send raw Empire protocol commands from the
    terminal.
ES: Punto de entrada. Lanza Chrome, conecta el relay CDP, arranca el
    puente HTTP, y permite enviar comandos crudos del protocolo Empire
    desde la terminal.
"""

import os
import readline
import sys
import time

import lib.empire_decoder as empire_decoder
from lib.empire_decoder import RAW_LOG, DECODED_LOG, EVENTS_LOG
from lib.gge_socket_browser import GgeSocketBrowser
from lib.gge_browser_selenium import connect_with_browser
from lib.bridge_server import BridgeServer
from lib.colors import colors


def _rotate_logs():
    """
    EN: Rotate logs on startup: if a log exists and is larger than 50 MB,
        rename it with a timestamp suffix instead of appending forever.
    ES: Rotar logs al arrancar: si un log existe y pesa mas de 50 MB,
        renombrarlo con sufijo de timestamp en vez de appendear siempre.
    """
    # EN: Paths come from empire_decoder so there is a single source of
    #     truth. Rotation only renames the file; the old data is kept
    #     under the timestamped name.
    # ES: Los paths vienen del empire_decoder para tener una sola fuente
    #     de verdad. La rotacion solo renombra el archivo; los datos
    #     viejos quedan bajo el nombre con timestamp.
    for path in (RAW_LOG, DECODED_LOG, EVENTS_LOG):
        try:
            if os.path.exists(path) and os.path.getsize(path) > 50 * 1024 * 1024:
                rotated = f"{path}.{time.strftime('%Y%m%d_%H%M%S')}"
                os.rename(path, rotated)
                print(f"[i] Rotated {path} -> {rotated}", flush=True)
        except Exception as e:
            print(f"[!] rotate error on {path}: {e}", flush=True)


def print_preserve_input(message):
    """
    EN: Print a message without losing the line currently being typed.
    ES: Imprime un mensaje sin perder la linea que se esta escribiendo.
    """
    input_buf = readline.get_line_buffer()
    sys.stdout.write(f"\x1b[2K\r{message}\n> {input_buf}")
    sys.stdout.flush()


if __name__ == '__main__':
    # EN: Rotate oversized logs before importing anything that opens them.
    #     empire_decoder now uses lazy-open (init_logs), so no file handle
    #     exists until the first write. Rotation is effective.
    # ES: Rotar logs gigantes antes de importar nada que los abra.
    #     empire_decoder ahora usa apertura perezosa (init_logs), asi que
    #     no existe ningun handle hasta la primera escritura. La rotacion
    #     es efectiva.
    _rotate_logs()

    # EN: Callback container. In the CDP relay architecture this object
    #     does not open a real WebSocket; it only holds callbacks.
    #     on_send and on_message are intentionally None: the decoder in
    #     gge_browser_selenium already prints every frame (raw is also
    #     written to RAW_LOG / DECODED_LOG). Setting them here would
    #     duplicate every line on the terminal.
    # ES: Contenedor de callbacks. En la arquitectura de relay CDP este
    #     objeto no abre un WebSocket real; solo guarda callbacks.
    #     on_send y on_message quedan en None a proposito: el decoder en
    #     gge_browser_selenium ya imprime cada frame (y ademas el crudo
    #     va a RAW_LOG / DECODED_LOG). Setearlos aca duplicaria cada
    #     linea en la terminal.
    socket = GgeSocketBrowser(
        on_send=None,
        on_open=lambda ws: print_preserve_input(colors.LIGHT_MAGENTA + 'WebSocket opened' + colors.ENDC),
        on_message=None,
        on_error=lambda ws, error: print_preserve_input(colors.LIGHT_RED + f"Error in websocket: {error}" + colors.ENDC),
        on_close=lambda ws, close_status_code, close_msg: print_preserve_input(colors.LIGHT_MAGENTA + f'WebSocket closed with code {close_status_code} and message {close_msg}' + colors.ENDC),
    )

    # EN: Start the HTTP bridge. It picks up the relay once Chrome is
    #     connected (the socket exposes .cdp_relay dynamically), so it is
    #     safe to start before connect_with_browser().
    # ES: Arrancar el puente HTTP. Toma el relay una vez que Chrome este
    #     conectado (el socket expone .cdp_relay dinamicamente), asi que
    #     es seguro arrancarlo antes de connect_with_browser().
    bridge = BridgeServer(socket, host="0.0.0.0", port=4444, timeout=15.0)
    empire_decoder.set_response_callback(bridge.handle_response)
    bridge.start()
    print(
        "[PY] Bridge HTTP listening on / Escuchando en http://0.0.0.0:4444",
        flush=True,
    )

    # EN: Launch Chrome and start the CDP relay.
    #     To target a non-GGS host, pass game_domain="your.host.com".
    # ES: Lanza Chrome y arranca el relay CDP.
    #     Para apuntar a un host que no sea GGS, pasar game_domain="tu.host".
    connect_with_browser(
        socket,
        'https://danadum.github.io/empire',
        8765,
        # game_domain="empire-html5.goodgamestudios.com",
    )

    # EN: REPL loop. Whatever is typed here is forwarded to the game via CDP.
    #     Special local commands (starting with '/') are handled here and
    #     not forwarded to the game.
    # ES: Bucle REPL. Lo que se escriba aca se reenvia al juego via CDP.
    #     Los comandos locales (que empiezan con '/') se manejan aca y
    #     no se reenvian al juego.
    while True:
        try:
            msg = input("> ")
        except EOFError:
            break
        if not msg:
            continue

        # EN: Local command: /full -> disable truncation of decoded JSON.
        # ES: Comando local: /full -> desactiva el truncado del JSON decodificado.
        if msg.strip() in ("/full", "/full on"):
            empire_decoder.DECODED_PREVIEW_MAX = None
            print("[i] Full JSON mode ON / Modo JSON completo ACTIVADO")
            continue

        # EN: Local command: /full off -> restore truncation (400 chars).
        # ES: Comando local: /full off -> restaura el truncado (400 chars).
        if msg.strip() == "/full off":
            empire_decoder.DECODED_PREVIEW_MAX = 400
            print("[i] Full JSON mode OFF (400 chars) / Modo JSON completo DESACTIVADO")
            continue

        # EN: Local command: /full <n> -> custom truncation limit.
        # ES: Comando local: /full <n> -> limite de truncado custom.
        if msg.strip().startswith("/full "):
            parts = msg.strip().split()
            if len(parts) == 2:
                try:
                    empire_decoder.DECODED_PREVIEW_MAX = int(parts[1])
                    print(f"[i] Truncation limit set to {parts[1]} / Limite de truncado: {parts[1]}")
                    continue
                except ValueError:
                    pass
            print("[!] Usage / Uso: /full | /full on | /full off | /full <n>")
            continue

        relay = getattr(socket, "cdp_relay", None)
        if relay is None:
            print("[!] Relay not ready yet. Wait for 'CDP relay activo'.")
            print("[!] El relay todavia no esta listo. Espera a 'CDP relay activo'.")
            continue
        try:
            relay.send_to_game(msg)
            # EN: No print here. The SENT frame is shown as [SENT] [CMD] ...
            #     by the decoder once CDP captures it. Avoids a duplicate line.
            # ES: Sin print. El frame SENT aparece como [SENT] [CMD] ...
            #     cuando el CDP lo captura. Evita una linea duplicada.
        except Exception as e:
            print(f"[!] Error: {e}")