"""
EN: Legacy file. In the pre-CDP architecture this class opened its own
    WebSocket to the game server. In the current CDP relay architecture
    it is only used as a callback container by main.py.
ES: Archivo legado. En la arquitectura previa al CDP esta clase abria su
    propio WebSocket al servidor del juego. En la arquitectura actual de
    relay CDP solo se usa como contenedor de callbacks por main.py.
"""

import threading

from pygge.gge_socket import GgeSocket


# EN: NOTE: the old monkey-patch that forced Chrome-like headers on every
#     websocket.WebSocketApp instance has been removed. It leaked a GGS
#     Origin header into the CdpRelay's own WebSocketApp connection to
#     Chrome (a global side effect), and the current CDP pipeline never
#     opens a game WebSocket from Python anyway. If you ever need those
#     headers again for the legacy path, set them explicitly on the
#     WebSocketApp(...) call instead of patching the class globally.
# ES: NOTA: el viejo monkey-patch que forzaba headers tipo Chrome en toda
#     instancia de websocket.WebSocketApp fue eliminado. Filtraba un
#     header Origin de GGS hacia la conexion WebSocketApp que CdpRelay
#     abre contra Chrome (side-effect global), y ademas el pipeline CDP
#     actual nunca abre un WebSocket del juego desde Python. Si alguna
#     vez necesitas esos headers de nuevo para el path legado, ponelos
#     explicitamente en la llamada WebSocketApp(...) en vez de parchear
#     la clase globalmente.


class GgeSocketBrowser(GgeSocket):
    """
    EN: Callback holder. main.py passes on_send / on_open / on_message /
        on_error / on_close, which are then called by the CDP relay.
    ES: Contenedor de callbacks. main.py pasa on_send / on_open /
        on_message / on_error / on_close, que luego el relay CDP llama.
    """

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, "ep-", None, *args, **kwargs)

    def __init__(
        self, on_send=None, on_open=None, on_message=None, on_error=None, on_close=None
    ):
        self.onsend = on_send
        self.onopen = on_open
        self.onmessage = on_message
        self.onerror = on_error
        self.onclose = on_close
        self.ws_server = None
        # EN: Set by connect_with_browser once the relay is ready.
        # ES: Lo setea connect_with_browser cuando el relay esta listo.
        self.cdp_relay = None

    # EN: Legacy methods below. Kept for backwards compatibility only.
    # ES: Metodos legados. Se mantienen solo por compatibilidad.

    def open(self, url):
        super().__init__(
            url,
            None,
            on_send=self.onsend,
            on_open=self.__onopen,
            on_message=self.__onmessage,
            on_error=self.onerror,
            on_close=self.__onclose,
        )
        threading.Thread(target=self.run_forever, daemon=True).start()

    def set_server_header(self, server_header):
        self.server_header = server_header

    def set_ws_server(self, ws_server):
        self.ws_server = ws_server

    def __onopen(self, ws):
        self.onopen and self.onopen(ws)
        self.ws_server.broadcast_sync(f"open")

    def __onmessage(self, ws, message):
        self.onmessage and self.onmessage(ws, message)
        self.ws_server.broadcast_sync(message.encode("UTF-8"))

    def __onclose(self, ws, close_status_code, close_msg):
        self.onclose and self.onclose(ws, close_status_code, close_msg)
        self.ws_server.close_connections_sync()