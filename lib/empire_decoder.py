"""
EN: EmpireEx protocol decoder. Handles the raw EmpireEx text frames
    used by Goodgame Empire, including the base64-wrapped variant
    (starts with 'JXh0' == base64('%xt')). Writes both the raw payload
    and the decoded text to separate log files.
ES: Decodificador del protocolo EmpireEx. Maneja los frames de texto
    EmpireEx usados por Goodgame Empire, incluida la variante envuelta
    en base64 (empieza con 'JXh0' == base64('%xt')). Escribe tanto el
    payload crudo como el texto decodificado a archivos de log separados.
"""

import base64
import json
import os
import re
import time

# EN: Raw log file for auditing every frame without truncation.
# ES: Archivo de log crudo para auditar todos los frames sin truncar.
RAW_LOG = "/tmp/gge_raw.log"
# EN: Decoded log: same frames but with base64 blobs expanded to text.
# ES: Log decodificado: los mismos frames pero con los blobs base64
#     expandidos a texto.
DECODED_LOG = "/tmp/gge_decoded.log"
# EN: Events log: a replayable timeline of player actions. Every SENT
#     frame except the ones the client sends on its own (heartbeats,
#     auto UI refresh). RECV frames are NOT written here on purpose:
#     this file is meant to list "things the user asked for", so it can
#     be replayed back into the game. Server replies remain available in
#     gge_raw.log and gge_decoded.log. Each line is prefixed with a
#     timestamp.
# ES: Log de eventos: una linea de tiempo reproducible de acciones del
#     jugador. Todos los frames SENT salvo los que el cliente manda por
#     su cuenta (heartbeats, auto-refresh de UI). Los frames RECV NO se
#     escriben aca a proposito: este archivo lista "cosas que el usuario
#     pidio", para poder reenviarlas al juego. Las respuestas del server
#     quedan en gge_raw.log y gge_decoded.log. Cada linea con timestamp.
EVENTS_LOG = "/tmp/gge_events.log"

# EN: Commands the game client sends on its own (heartbeats, auto UI
#     refresh). These are NOT player actions and would flood the events
#     log. Anything else sent by the client is considered a player
#     action and gets logged.
# ES: Comandos que el cliente del juego manda por su cuenta (heartbeats,
#     auto-refresh de UI). NO son acciones del jugador y llenarian el
#     log de eventos. Cualquier otra cosa que mande el cliente se
#     considera accion del jugador y se loguea.
AUTO_SENT_COMMANDS = {
    "pin",   # heartbeat / latido
    "gui",   # auto UI refresh / auto-refresh de UI
}

# EN: Max characters of the decoded payload to show on the terminal.
#     Set GGE_DECODED_FULL=1 to disable truncation entirely.
#     Set GGE_DECODED_MAX=<n> to use a custom character limit.
# ES: Maximo de caracteres del payload decodificado a mostrar en terminal.
#     Poner GGE_DECODED_FULL=1 desactiva el truncado por completo.
#     Poner GGE_DECODED_MAX=<n> usa un limite de caracteres custom.
if os.environ.get("GGE_DECODED_FULL", "").strip().lower() in ("1", "true", "yes", "on"):
    # EN: No truncation. / ES: Sin truncado.
    DECODED_PREVIEW_MAX = None
else:
    try:
        DECODED_PREVIEW_MAX = int(os.environ.get("GGE_DECODED_MAX", "400"))
    except ValueError:
        DECODED_PREVIEW_MAX = 400

# EN: Friendly names for common EmpireEx commands.
# ES: Nombres legibles para comandos EmpireEx comunes.
FRIENDLY_CMD = {
    "sii": "ServerInfoInit",
    "hgh": "Highscore",
    "ama": "AllianceMembers",
    "irc": "InitResourceCastle",
    "pin": "Ping",
    "llp": "LoginLastPlayer",
    "lli": "LoginInfo",
    "gpi": "GetPlayerInfo",
    "gat": "GetAllianceTasks",
    "all": "AllianceList",
    "asc": "AskCastle",
    "grc": "GetResourcesCastle",
    "gam": "GameMessage",
}

# EN: Lazy-opened file handles. Open on first write, not at import time,
#     so main.py can rotate old logs BEFORE any handle is created.
# ES: File handles de apertura perezosa. Se abren en la primera escritura,
#     no al importar, para que main.py pueda rotar los logs viejos ANTES
#     de que exista algun handle.
_raw_fp = None
_decoded_fp = None
_events_fp = None

# EN: Global response callback. Set by main.py so the HTTP bridge can
#     pick up every decoded RECV frame and match it to pending requests.
# ES: Callback global de respuesta. Lo setea main.py para que el puente
#     HTTP capture cada frame RECV decodificado y lo matchee con
#     peticiones pendientes.
_response_callback = None


def set_response_callback(cb):
    """
    EN: Register a callback invoked for every decoded RECV frame.
        Signature: cb(cmd: str, json_body: any)
    ES: Registrar un callback invocado para cada frame RECV decodificado.
        Firma: cb(cmd: str, json_body: any)
    """
    global _response_callback
    _response_callback = cb


def init_logs():
    """
    EN: Open the log files if they are not already open. Idempotent.
        Call this once after any rotation, or rely on _log_event /
        format_payload to call it on first use.
    ES: Abre los archivos de log si no estan abiertos. Idempotente.
        Llamar una vez despues de cualquier rotacion, o confiar en que
        _log_event / format_payload lo llamen en el primer uso.
    """
    global _raw_fp, _decoded_fp, _events_fp
    if _raw_fp is None:
        _raw_fp = open(RAW_LOG, "a", buffering=1)
    if _decoded_fp is None:
        _decoded_fp = open(DECODED_LOG, "a", buffering=1)
    if _events_fp is None:
        _events_fp = open(EVENTS_LOG, "a", buffering=1)


def _log_event(cmd, direction, decoded):
    """
    EN: Log ONLY player actions to the events file: every SENT frame
        except the ones the client sends on its own (heartbeats, auto UI
        refresh). RECV frames are intentionally NOT logged here: this
        file is meant to be a replayable timeline of "things the user
        asked for", so it can be scripted back into the game. Server
        replies remain available in gge_raw.log and gge_decoded.log.
    ES: Loguea SOLO acciones del jugador al archivo de eventos: todos
        los frames SENT salvo los que el cliente manda por su cuenta
        (heartbeats, auto-refresh de UI). Los frames RECV NO se loguean
        aca a proposito: este archivo es una linea de tiempo reproducible
        de "cosas que el usuario pidio", para poder reenviarlas al juego
        como script. Las respuestas del server siguen disponibles en
        gge_raw.log y gge_decoded.log.
    """
    # EN: Ensure handles are open (lazy open).
    # ES: Asegurar que los handles estan abiertos (apertura perezosa).
    init_logs()
    if direction != "SENT":
        return
    if cmd and cmd not in AUTO_SENT_COMMANDS:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        _events_fp.write(f"[{ts}] [SENT] [{cmd}] {decoded}\n")


def _decode_b64_empire(payload):
    """
    EN: Decode a base64 payload if it looks like an EmpireEx frame
        (starts with 'JXh0' == base64('%xt')). Returns decoded text or
        None if it is not a base64 EmpireEx blob.
    ES: Decodifica un payload base64 si parece un frame EmpireEx
        (empieza con 'JXh0' == base64('%xt')). Devuelve el texto
        decodificado o None si no es un blob EmpireEx en base64.
    """
    if not payload.startswith("JXh0"):
        return None
    try:
        raw = base64.b64decode(payload)
    except Exception as e:
        return f"<b64 decode error: {e}>"
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_json(decoded):
    """
    EN: Extract the JSON body from a decoded EmpireEx frame. Robust
        against '%' characters appearing inside the JSON. Returns
        (json_str, prefix) or (None, None).
    ES: Extrae el cuerpo JSON de un frame EmpireEx decodificado.
        Robusto ante caracteres '%' dentro del JSON. Devuelve
        (json_str, prefix) o (None, None).
    """
    start = -1
    for i, c in enumerate(decoded):
        if c in "{[":
            start = i
            break
    if start < 0:
        return None, None
    for i in range(len(decoded) - 1, start, -1):
        if decoded[i] in "}]":
            return decoded[start:i + 1], decoded[:start]
    return None, None


def _find_command(prefix):
    """
    EN: Find the EmpireEx command code inside the frame prefix, e.g.
        '%xt%all%1%0%' -> 'all'; '%xt%EmpireEx_25%hgh%1%' -> 'hgh'.
    ES: Encuentra el codigo de comando EmpireEx dentro del prefijo,
        ej. '%xt%all%1%0%' -> 'all'; '%xt%EmpireEx_25%hgh%1%' -> 'hgh'.
    """
    if not prefix:
        return None
    parts = prefix.strip("%").split("%")
    for p in parts:
        if p == "xt":
            continue
        if p in FRIENDLY_CMD:
            return p
    for p in parts:
        if p != "xt" and re.fullmatch(r"[a-z]{2,4}", p):
            return p
    return None


def _summarize_json(obj):
    """
    EN: One-line compact description of a decoded JSON body.
    ES: Descripcion compacta de una linea de un cuerpo JSON decodificado.
    """
    if isinstance(obj, dict):
        keys = list(obj.keys())
        shown = keys[:10]
        extra = f" (+{len(keys) - 10} more)" if len(keys) > 10 else ""
        return f"dict keys={shown}{extra}"
    if isinstance(obj, list):
        out = f"list len={len(obj)}"
        if obj and isinstance(obj[0], dict):
            out += f" first_keys={list(obj[0].keys())[:8]}"
        return out
    return f"{type(obj).__name__}={str(obj)[:80]}"


def _format_empire_text(decoded, direction):
    """
    EN: Build a human-readable line for a decoded EmpireEx text frame.
        The raw EmpireEx header (the part before the JSON body, e.g.
        'xt%EmpireEx_25%bup%1%0') is shown alongside the friendly name
        so the full frame prefix is visible on the terminal.
    ES: Construye una linea legible para un frame EmpireEx ya decodificado.
        El header crudo de EmpireEx (la parte antes del cuerpo JSON, ej.
        'xt%EmpireEx_25%bup%1%0') se muestra junto al nombre amigable
        para que el prefijo completo del frame sea visible en terminal.
    """
    if not decoded.startswith("%xt%"):
        # EN: Full output mode: no truncation.
        # ES: Modo salida completa: sin truncado.
        if DECODED_PREVIEW_MAX is None:
            return f"[{direction}] [TXT] {decoded}"
        preview = decoded[:DECODED_PREVIEW_MAX]
        suffix = "..." if len(decoded) > DECODED_PREVIEW_MAX else ""
        return f"[{direction}] [TXT] {preview}{suffix}"

    json_str, prefix = _extract_json(decoded)
    cmd = _find_command(prefix)
    friendly = FRIENDLY_CMD.get(cmd, cmd or "?")

    # EN: Strip the outer % so the header reads as
    #     'xt%EmpireEx_25%bup%1%0' instead of '%xt%...%'.
    # ES: Recortar los % externos para que el header se lea como
    #     'xt%EmpireEx_25%bup%1%0' en vez de '%xt%...%'.
    header = prefix.strip("%") if prefix else ""

    # EN: Log to the events file following the SENT/RECV rules.
    # ES: Loguear al archivo de eventos siguiendo las reglas SENT/RECV.
    _log_event(cmd, direction, decoded)

    if not json_str:
        # EN: Notify the bridge even for bodyless frames.
        # ES: Notificar al puente incluso para frames sin cuerpo.
        if direction == "RECV" and _response_callback is not None:
            try:
                _response_callback(cmd, None)
            except Exception as e:
                print(f"[decoder] response callback error: {e}", flush=True)
        return f"[{direction}] [CMD] {header} ({friendly})"

    try:
        obj = json.loads(json_str)
    except Exception:
        # EN: Raw (unparsable) JSON body.
        # ES: Cuerpo JSON crudo (no parseable).
        if direction == "RECV" and _response_callback is not None:
            try:
                _response_callback(cmd, None)
            except Exception as e:
                print(f"[decoder] response callback error: {e}", flush=True)
        if DECODED_PREVIEW_MAX is None:
            return f"[{direction}] [CMD] {header} ({friendly}) (raw) {json_str}"
        preview = json_str[:DECODED_PREVIEW_MAX]
        suffix = "..." if len(json_str) > DECODED_PREVIEW_MAX else ""
        return f"[{direction}] [CMD] {header} ({friendly}) (raw) {preview}{suffix}"

    # EN: Notify the HTTP bridge (only for RECV frames). Done before
    #     formatting so the HTTP waiter unblocks as fast as possible.
    # ES: Notificar al puente HTTP (solo para frames RECV). Se hace antes
    #     del formateo para que el waiter HTTP se desbloquee lo antes
    #     posible.
    if direction == "RECV" and _response_callback is not None:
        try:
            _response_callback(cmd, obj)
        except Exception as e:
            print(f"[decoder] response callback error: {e}", flush=True)

    summary = _summarize_json(obj)
    try:
        pretty = json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        pretty = json_str

    head = f"[{direction}] [CMD] {header} ({friendly}) ({summary})"

    # EN: Full output mode: no truncation.
    # ES: Modo salida completa: sin truncado.
    if DECODED_PREVIEW_MAX is None:
        return f"{head}\n{pretty}"
    preview = pretty[:DECODED_PREVIEW_MAX]
    suffix = "\n..." if len(pretty) > DECODED_PREVIEW_MAX else ""
    return f"{head}\n{preview}{suffix}"


def format_payload(payload, direction):
    """
    EN: Convert a raw WebSocket frame into a human-readable line.
    ES: Convierte un frame WebSocket crudo en una linea legible.
    direction: "RECV" (from server) or "SENT" (from client).
    """
    # EN: Ensure handles are open (lazy open). No-op after the first call.
    # ES: Asegurar que los handles estan abiertos (apertura perezosa).
    #     No-op despues de la primera llamada.
    init_logs()

    # EN: Always write the raw frame to file first.
    # ES: Siempre escribimos el frame crudo al archivo primero.
    _raw_fp.write(f"\n=== {direction} ({len(payload)} bytes) ===\n{payload}\n")

    # EN: Base64-encoded EmpireEx blob -> decode and format.
    # ES: Blob EmpireEx en base64 -> decodificar y formatear.
    decoded = _decode_b64_empire(payload)
    if decoded is not None:
        _decoded_fp.write(
            f"\n=== {direction} ({len(payload)} b64 -> {len(decoded)} txt) ===\n"
            f"{decoded}\n"
        )
        inner = _format_empire_text(decoded, direction)
        return f"[{direction}] [BIN->TXT] ({len(payload)} b64) {inner}"

    # EN: SmartFox XML message.
    # ES: Mensaje XML de SmartFox.
    if payload.startswith("<"):
        m = re.match(
            r"<msg t='(.*?)'><body action='(.*?)' r='(.*?)'>(.*?)</body></msg>",
            payload,
        )
        if m:
            t, action, r, data = m.groups()
            return f"[{direction}] [XML] t={t} action={action} r={r} data={data[:120]}"
        return f"[{direction}] [XML] {payload[:120]}"

    # EN: Plain EmpireEx text frame (no base64).
    # ES: Frame EmpireEx de texto plano (sin base64).
    if payload.startswith("%xt%"):
        return _format_empire_text(payload, direction)

    # EN: Unknown format.
    # ES: Formato desconocido.
    return f"[{direction}] [???] {payload[:120]}"