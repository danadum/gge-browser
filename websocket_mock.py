from gge_browser_selenium import connect_with_browser

class WebSocketMock:
    def __init__(self):
        pass

    def close(self):
        pass

class WebSocketAppMock:
    def __init__(self, url, on_open=None, on_message=None, on_error=None, on_close=None, on_send=None, on_log=None, game_url='https://empire.goodgamestudios.com', ws_server_port=8765):
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_send = on_send
        self.on_log = on_log
        self.game_url = game_url
        self.ws_server = None
        self.ws_server_port = ws_server_port

        self.sock = WebSocketMock()

    def send(self, message):
        self.ws_server.broadcast_sync(message)
    
    def close(self):
        if self.ws_server:
            self.ws_server.close()
    
    def run_forever(self, *args, **kwargs):
        connect_with_browser(self, self.game_url, self.ws_server_port)