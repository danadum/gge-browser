import asyncio
import websockets
import threading


class WebsocketServer:
    def __init__(self, port, on_message=None, on_start=None, on_close=None, on_connection=None, on_disconnection=None):
        self.port = port
        self.on_message = on_message
        self.on_start = on_start
        self.on_close = on_close
        self.on_connection = on_connection
        self.on_disconnection = on_disconnection
        self.clients = []
        self.closed = asyncio.Event()

    async def handler(self, websocket):
        self.on_connection and self.on_connection(websocket)
        self.clients.append(websocket)
        try:
            async for message in websocket:
                self.on_message and self.on_message(websocket, message)
        finally:
            self.on_disconnection and self.on_disconnection(websocket)
            self.clients.remove(websocket)

    async def start(self):
        async with websockets.serve(self.handler, "localhost", self.port):
            self.on_start and self.on_start()
            await self.closed.wait()
        self.on_close and self.on_close()
    
    def start_sync(self):
        asyncio.run(self.start())

    async def broadcast(self, message):
        for client in self.clients:
            await client.send(message)

    def broadcast_sync(self, message):
        thread = threading.Thread(target=lambda: asyncio.run(self.broadcast(message)), daemon=True)
        thread.start()
        thread.join()

    async def close_connections(self):
        for client in self.clients:
            await client.close()
        self.clients.clear()
        self.closed.set()

    def close_connections_sync(self):
        thread = threading.Thread(target=lambda: asyncio.run(self.close_connections()), daemon=True)
        thread.start()
        thread.join()

    async def close(self):
        self.closed.set()
