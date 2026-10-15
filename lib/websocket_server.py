"""
EN: Legacy file. Local WebSocket server used by the pre-CDP architecture
    as a proxy between the browser and pygge. Not used by the current CDP
    relay pipeline; kept for backwards compatibility.
ES: Archivo legado. Servidor WebSocket local usado por la arquitectura
    previa al CDP como proxy entre el navegador y pygge. No lo usa el
    pipeline actual de relay CDP; se mantiene por compatibilidad.
"""

import asyncio
import websockets
import threading


class WebsocketServer:
    """
    EN: Async WebSocket server with a synchronous facade.
    ES: Servidor WebSocket asincrono con una fachada sincrona.
    """

    def __init__(self, port, on_message=None, on_start=None, on_close=None, on_connection=None, on_disconnection=None):
        self.port = port
        self.on_message = on_message
        self.on_start = on_start
        self.on_close = on_close
        self.on_connection = on_connection
        self.on_disconnection = on_disconnection
        self.clients = []
        self.closed = asyncio.Event()
        self.loop = None

    async def handler(self, websocket):
        # EN: Per-connection coroutine: register, stream, unregister.
        # ES: Corrutina por conexion: registra, escucha, desregistra.
        self.on_connection and self.on_connection(websocket)
        self.clients.append(websocket)
        try:
            async for message in websocket:
                self.on_message and self.on_message(websocket, message)
        finally:
            self.on_disconnection and self.on_disconnection(websocket)
            if websocket in self.clients:
                self.clients.remove(websocket)

    async def start(self):
        # EN: Bind the port and wait until closed.
        # ES: Vincula el puerto y espera hasta que se cierre.
        async with websockets.serve(self.handler, "localhost", self.port):
            self.on_start and self.on_start()
            await self.closed.wait()
        self.on_close and self.on_close()

    def start_sync(self):
        # EN: Run the async server on a dedicated event loop.
        # ES: Corre el servidor asincrono en un event loop dedicado.
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start())

    async def broadcast(self, message):
        # EN: Send a message to every connected client.
        # ES: Envia un mensaje a todos los clientes conectados.
        for client in list(self.clients):
            try:
                await client.send(message)
            except Exception as e:
                print(f"[WS] broadcast failed: {e}")

    def broadcast_sync(self, message):
        # EN: Thread-safe wrapper around broadcast().
        # ES: Envoltorio thread-safe de broadcast().
        if self.loop and self.loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
            try:
                fut.result(timeout=2)
            except Exception as e:
                print(f"[WS] broadcast_sync error: {e}")

    async def close_connections(self):
        # EN: Close every client connection and mark the server closed.
        # ES: Cierra todas las conexiones de clientes y marca el server cerrado.
        for client in list(self.clients):
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()
        self.closed.set()

    def close_connections_sync(self):
        # EN: Use run_coroutine_threadsafe, NOT asyncio.run(): clients
        #     belong to the original loop, not to a new one.
        # ES: Usar run_coroutine_threadsafe, NO asyncio.run(): los clientes
        #     pertenecen al loop original, no a uno nuevo.
        if self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.close_connections(), self.loop)
            except Exception as e:
                print(f"[WS] close_connections_sync error: {e}")
        else:
            self.clients.clear()
            try:
                self.closed.set()
            except Exception:
                pass

    async def close(self):
        # EN: Signal the server loop to stop.
        # ES: Senaliza al loop del servidor que se detenga.
        self.closed.set()