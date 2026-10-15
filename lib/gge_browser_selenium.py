"""
EN: Launches Chrome with the flags needed for the CDP relay to work,
    waits for the game iframe, and connects the relay.
ES: Lanza Chrome con las flags necesarias para el relay CDP,
    espera el iframe del juego, y conecta el relay.
"""

import readline
import sys
import threading
import traceback
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from lib.cdp_relay import CdpRelay
from lib.empire_decoder import format_payload, RAW_LOG, DECODED_LOG
from lib.colors import colors


def _print_preserving_input(message):
    input_buf = readline.get_line_buffer()
    sys.stdout.write(f"\x1b[2K\r{message}\n> {input_buf}")
    sys.stdout.flush()


def open_browser(game_url):
    """
    EN: Launch Chrome with the flags required for CDP relay.
    ES: Lanza Chrome con las flags requeridas para el relay CDP.
    """
    port = 9222
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={os.path.join(os.getcwd(), 'user-data')}")
    options.add_argument(f"--remote-debugging-port={port}")
    # EN: Required for Chrome to accept the CDP WebSocket connection.
    # ES: Necesario para que Chrome acepte la conexion WebSocket al CDP.
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-features=Translate")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("detach", True)

    print("[PY] Launching Chrome... / Lanzando Chrome...", flush=True)
    driver = webdriver.Chrome(options=options)
    print(f"[PY] Chrome: {driver.capabilities.get('browserVersion')}", flush=True)

    driver.switch_to.window(driver.window_handles[-1])
    driver.get(game_url)
    print(f"[PY] Navigated to / Navegando a: {driver.current_url}", flush=True)
    return driver, port


def connect_with_browser(socket, game_url, ws_server_port,
                         game_domain="goodgamestudios.com"):
    """
    EN: Launch Chrome, wait for the game iframe, and connect the CDP relay.
        The socket object is only used as a callback container.
        game_domain is forwarded to CdpRelay so the relay is not hardcoded
        to goodgamestudios.com.
    ES: Lanza Chrome, espera el iframe del juego, y conecta el relay CDP.
        El objeto socket solo se usa como contenedor de callbacks.
        game_domain se reenvia a CdpRelay para no cablear el relay a
        goodgamestudios.com.
    """
    driver, debug_port = open_browser(game_url)

    def on_recv(payload):
        try:
            _print_preserving_input(
                colors.LIGHT_BLUE + format_payload(payload, "RECV") + colors.ENDC
            )
        except Exception as e:
            _print_preserving_input(f"[RECV] <format error: {e}>")
        if socket.onmessage:
            try:
                socket.onmessage(None, payload)
            except Exception:
                pass

    def on_sent(payload):
        # EN: Called for each frame the game client sends. Printed in
        #     LIGHT_GREEN, so commands typed in the REPL (and any
        #     automatic client send) stand out in green.
        # ES: Se llama por cada frame que envia el cliente del juego.
        #     Impreso en LIGHT_GREEN, para que los comandos escritos en
        #     el REPL (y cualquier envio automatico del cliente) resalten
        #     en verde.
        try:
            _print_preserving_input(
                colors.LIGHT_GREEN + format_payload(payload, "SENT") + colors.ENDC
            )
        except Exception as e:
            _print_preserving_input(f"[SENT] <format error: {e}>")
        if socket.onsend:
            try:
                socket.onsend(None, payload)
            except Exception:
                pass

    relay = CdpRelay(
        debug_port=debug_port,
        game_domain=game_domain,
        on_frame_recv=on_recv,
        on_frame_sent=on_sent,
        on_error=lambda e: _print_preserving_input(f"[CDP] err: {e}"),
    )

    def wait_and_connect():
        # EN: Wait for the game iframe, then connect the relay.
        #     No fixed sleeps: connect() blocks on the CDP open event,
        #     and wait_ready() blocks on the hook-installed event.
        # ES: Espera el iframe del juego, despues conecta el relay.
        #     Sin sleeps fijos: connect() bloquea en el evento de apertura
        #     del CDP, y wait_ready() bloquea en el evento de hook
        #     instalado.
        _print_preserving_input("[PY] Waiting for iframe#game... / Esperando iframe#game...")
        try:
            WebDriverWait(driver, 90, poll_frequency=0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe#game'))
            )
            _print_preserving_input("[PY] iframe found, connecting CDP relay / iframe encontrado, conectando relay CDP")
            relay.connect(timeout=15)
            if relay.wait_ready(timeout=20):
                _print_preserving_input("[PY] CDP relay active. / CDP relay activo.")
            else:
                _print_preserving_input("[PY] CDP relay connected but hook install timed out. / El relay conecto pero el hook no se instalo a tiempo.")
            _print_preserving_input(f"[PY] Raw log / Log crudo: {RAW_LOG}")
            _print_preserving_input(f"[PY] Decoded log / Log decodificado: {DECODED_LOG}")
            socket.cdp_relay = relay
        except Exception as e:
            _print_preserving_input(f"[PY] Error waiting for iframe / Error esperando iframe: {e}")
            traceback.print_exc()

    threading.Thread(target=wait_and_connect, daemon=True).start()