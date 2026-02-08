import threading

from pygge.gge_socket import GgeSocket


class GgeSocketBrowser(GgeSocket):
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

    def open(self, url):
        super().__init__(url, None, on_send=self.onsend, on_open=self.__onopen, on_message=self.__onmessage, on_error=self.onerror, on_close=self.__onclose)
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
        self.ws_server.broadcast_sync(message.encode('UTF-8'))

    def __onclose(self, ws, close_status_code, close_msg):
        self.onclose and self.onclose(ws, close_status_code, close_msg)
        self.ws_server.close_connections_sync()
