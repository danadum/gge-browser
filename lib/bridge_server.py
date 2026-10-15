"""
EN: HTTP bridge server. Exposes an empire-api-compatible REST API on top
    of the CDP relay. Any consumer that speaks to empire-api can instead
    speak to this bridge, gaining full session context (real Chrome login).
ES: Servidor HTTP puente. Expone una API REST compatible con empire-api
    sobre el relay CDP. Cualquier consumidor que hable con empire-api
    puede en cambio hablar con este puente, ganando contexto de sesion
    completo (login real de Chrome).
"""

import json
import logging
import threading
from flask import Flask, jsonify
from flask_cors import CORS

# EN: Map of request command -> response command when they differ.
#     Mirrors empire-api's ANSWERED_AS.
# ES: Mapa de comando pedido -> comando de respuesta cuando difieren.
#     Refleja el ANSWERED_AS de empire-api.
ANSWERED_AS = {
    "jca": "jaa",
}


class BridgeServer:
    def __init__(self, socket, host="0.0.0.0", port=4444, timeout=15.0):
        self.socket = socket
        self.host = host
        self.port = port
        self.timeout = timeout

        self.app = Flask("gge-bridge")
        CORS(self.app)

        # EN: pending[response_cmd] = threading.Event
        # ES: pending[response_cmd] = threading.Event
        self._pending = {}
        # EN: responses[response_cmd] = parsed JSON body
        # ES: responses[response_cmd] = cuerpo JSON parseado
        self._responses = {}
        self._lock = threading.Lock()
        self._stats = {"requests": 0, "timeouts": 0, "errors": 0}

        self._register_routes()

    def _register_routes(self):
        @self.app.route("/", methods=["GET"])
        def index():
            return jsonify({
                "service": "gge-browser bridge",
                "status": "ok",
                "stats": dict(self._stats),
            })

        # EN: Two routes: with params and without.
        # ES: Dos rutas: con params y sin params.
        @self.app.route("/<zone>/<cmd>", methods=["GET"])
        def handle_no_params(zone, cmd):
            return self._handle(zone, cmd, None)

        @self.app.route("/<zone>/<cmd>/<path:params>", methods=["GET"])
        def handle_with_params(zone, cmd, params):
            return self._handle(zone, cmd, params)

    def _handle(self, zone, cmd, params):
        self._stats["requests"] += 1

        # EN: Reconstruct the JSON body. empire-api URLs come with the
        #     body pieces already URL-decoded by Flask, e.g.
        #     '"LT":1,"LID":1,"SV":"1"'. We wrap in braces.
        # ES: Reconstruir el cuerpo JSON. Las URLs de empire-api llegan
        #     con las piezas ya URL-decodificadas por Flask, ej.
        #     '"LT":1,"LID":1,"SV":"1"'. Envolvemos en llaves.
        json_body = "null"
        if params:
            p = params.strip()
            if p.lower() == "null":
                json_body = "null"
            elif p.startswith("{"):
                json_body = p
            else:
                json_body = "{" + p + "}"

        # EN: Rebuild the raw game frame:
        #     %xt%<zone>%<cmd>%1%<json>%
        # ES: Reconstruir el frame crudo del juego:
        #     %xt%<zone>%<cmd>%1%<json>%
        frame = f"%xt%{zone}%{cmd}%1%{json_body}%"

        response_cmd = ANSWERED_AS.get(cmd, cmd)

        # EN: Reject concurrent requests for the same response command,
        #     since responses have no request id to match against.
        # ES: Rechazar peticiones concurrentes para el mismo comando de
        #     respuesta, ya que las respuestas no traen request id.
        event = threading.Event()
        with self._lock:
            if response_cmd in self._pending:
                self._stats["errors"] += 1
                return jsonify({
                    "error": "Another request for this command is in flight",
                    "return_code": -1,
                }), 429
            self._pending[response_cmd] = event
            self._responses.pop(response_cmd, None)

        relay = getattr(self.socket, "cdp_relay", None)
        if relay is None:
            with self._lock:
                self._pending.pop(response_cmd, None)
            self._stats["errors"] += 1
            return jsonify({
                "error": "Relay not ready (Chrome not logged in yet)",
                "return_code": -1,
            }), 503

        try:
            relay.send_to_game(frame)
        except Exception as e:
            with self._lock:
                self._pending.pop(response_cmd, None)
            self._stats["errors"] += 1
            return jsonify({
                "error": f"Send failed: {e}",
                "server": zone,
                "command": response_cmd,
                "return_code": -1,
            }), 500

        got = event.wait(timeout=self.timeout)
        with self._lock:
            self._pending.pop(response_cmd, None)
            data = self._responses.pop(response_cmd, None)

        if not got or data is None:
            self._stats["timeouts"] += 1
            return jsonify({
                "error": "Timeout",
                "server": zone,
                "command": response_cmd,
                "response_headers": self._parse_headers(json_body),
                "return_code": -1,
            }), 504

        self._stats["requests"] -= 0  # keep counter
        return jsonify({
            "server": zone,
            "command": response_cmd,
            "return_code": 0,
            "content": data,
        })

    def _parse_headers(self, json_body):
        try:
            if json_body and json_body != "null":
                return json.loads(json_body)
        except Exception:
            pass
        return None

    def handle_response(self, cmd, json_body):
        """
        EN: Called by the decoder for every RECV frame. Matches it to a
            pending request and unblocks the HTTP handler.
        ES: Llamado por el decoder para cada frame RECV. Lo matchea con
            una peticion pendiente y desbloquea el handler HTTP.
        """
        if cmd is None:
            return
        with self._lock:
            event = self._pending.get(cmd)
            if event is None:
                return
            self._responses[cmd] = json_body
        event.set()

    def start(self):
        def run():
            log = logging.getLogger("werkzeug")
            log.setLevel(logging.ERROR)
            self.app.run(
                host=self.host,
                port=self.port,
                threaded=True,
                debug=False,
                use_reloader=False,
            )

        thread = threading.Thread(target=run, daemon=True, name="bridge-http")
        thread.start()
        return thread

    def get_stats(self):
        return dict(self._stats)
