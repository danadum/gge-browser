# gge-browser

EN: Python library to open the game [Goodgame Empire](https://empire.goodgamestudios.com) in a browser with control over the game socket from the code.

ES: Libreria en Python para abrir el juego [Goodgame Empire](https://empire.goodgamestudios.com) en un navegador con control sobre el socket del juego desde el codigo.

---

## Status / Estado

EN: The original WebSocket proxy approach is broken on Chrome 145+. Chrome now blocks Private Network Access (PNA) between public HTTPS pages and `localhost`, uses Out-Of-Process IFrames (OOPIF), and rejects Python TLS fingerprints at the server WAF. This fork replaces the proxy with a **CDP relay** architecture:

- Chrome talks to Goodgame servers directly (native WebSocket).
- Python listens to WebSocket frames via Chrome DevTools Protocol (`Network.webSocketFrameReceived` / `Network.webSocketFrameSent`).
- Python injects commands via `Runtime.evaluate` on a passive hook installed over `WebSocket.prototype.send`.

This avoids binary corruption and TLS fingerprint detection.

ES: El metodo original de proxy WebSocket esta roto en Chrome 145+. Chrome ahora bloquea Private Network Access (PNA) entre paginas HTTPS publicas y `localhost`, usa iframes en procesos separados (OOPIF), y rechaza fingerprints TLS de Python en el WAF del servidor. Este fork reemplaza el proxy por una arquitectura de **relay CDP**:

- Chrome habla directo con los servidores de Goodgame (WebSocket nativo).
- Python escucha los frames WebSocket via Chrome DevTools Protocol (`Network.webSocketFrameReceived` / `Network.webSocketFrameSent`).
- Python inyecta comandos via `Runtime.evaluate` sobre un hook pasivo instalado en `WebSocket.prototype.send`.

Esto evita corrupcion binaria y deteccion por fingerprint TLS.

EN: On top of the relay, this fork adds an **HTTP bridge** (see [HTTP Bridge](#http-bridge--puente-http) below) that exposes an `empire-api`-compatible REST API. Backend services that already speak to `empire-api` can point at this bridge instead, gaining full session context (real Chrome login) and unlocking commands like `jca`, `gaa` and `gpi` that time out against the public `empire-api` fork.

ES: Sobre el relay, este fork agrega un **puente HTTP** (ver [HTTP Bridge](#http-bridge--puente-http) mas abajo) que expone una API REST compatible con `empire-api`. Los servicios que ya hablan con `empire-api` pueden apuntar a este puente, ganando contexto de sesion completo (login real de Chrome) y desbloqueando comandos como `jca`, `gaa` y `gpi` que dan timeout contra el fork publico de `empire-api`.

---

## Requirements / Requisitos

- **Google Chrome 145+** (tested on 155.0.8059.39)
- **Python 3.11+** (tested on 3.14)
- Linux, macOS, or Windows (see [Platform notes](#platform-notes--notas-de-plataforma) for Windows caveats)

Dependencies:

- `selenium >= 4.20`
- `websocket-client`
- `requests`
- `pygge` (from `requirements.txt`)
- `websockets`
- `flask` (for the HTTP bridge)
- `flask-cors` (for the HTTP bridge)

---

## Installation / Instalacion

EN: Clone the repository, create a virtual environment, and install the required dependencies.

ES: Clona el repositorio, crea un entorno virtual, e instala las dependencias requeridas.

```sh
git clone https://github.com/YOUR_USER/gge-browser.git
cd gge-browser

python -m venv .venv
source .venv/bin/activate     # Linux / macOS
# .venv\Scripts\activate      # Windows

pip install --upgrade pip
pip install -r requirements.txt
pip install flask flask-cors
```

EN: Make sure `google-chrome` is available on your PATH.

ES: Asegurate de que `google-chrome` este disponible en el PATH.

```sh
which google-chrome
google-chrome --version
```

EN: On Arch / EndeavourOS you may need to install it manually from the AUR:

ES: En Arch / EndeavourOS puede que necesites instalarlo manualmente desde AUR:

```sh
yay -S google-chrome
```

---

## Usage / Uso

EN: Run the entry point:

ES: Ejecuta el punto de entrada:

```sh
python -u main.py
```

EN: Chrome will open automatically, navigate to the wrapper page, and load the game inside an iframe. Once the game reaches its login screen:

1. Log in with your Goodgame account.
2. Wait until the terminal shows `CDP relay active.`
3. Type raw protocol commands at the `>` prompt.

ES: Chrome se abrira automaticamente, navegara a la pagina del wrapper, y cargara el juego dentro de un iframe. Una vez que el juego llegue a la pantalla de login:

1. Inicia sesion con tu cuenta de Goodgame.
2. Espera a que la terminal muestre `CDP relay active.`
3. Escribe comandos crudos del protocolo en el prompt `>`.

EN: The HTTP bridge starts before Chrome and listens on port `4444` by default. You will see:

```text
[PY] Bridge HTTP listening on / Escuchando en http://0.0.0.0:4444
```

ES: El puente HTTP arranca antes que Chrome y escucha en el puerto `4444` por defecto. Vas a ver:

```text
[PY] Bridge HTTP listening on / Escuchando en http://0.0.0.0:4444
```

EN: Example session output:

ES: Ejemplo de salida de sesion:

```text
[PY] Bridge HTTP listening on / Escuchando en http://0.0.0.0:4444
[PY] Launching Chrome... / Lanzando Chrome...
[PY] Chrome: 155.0.8059.39
[PY] Navigated to / Navegando a: https://danadum.github.io/empire/?nomobileredirect=true
[PY] Waiting for iframe#game... / Esperando iframe#game...
[PY] iframe found, connecting CDP relay / iframe encontrado, conectando relay CDP
[CDP] Connection open, enabling Network + Runtime
[CDP] Conexion abierta, habilitando Network + Runtime
[CDP] Runtime.evaluate id=2 -> HOOK_INSTALLED
[CDP] Game WebSocket created / WebSocket del juego creado: requestId=110298.144
[PY] CDP relay active. / CDP relay activo.
[PY] Raw log / Log crudo: /tmp/gge_raw.log
[PY] Decoded log / Log decodificado: /tmp/gge_decoded.log
> [RECV] [CMD] xt%grc%1 (GetResourcesCastle) (dict keys=['AID', 'W', 'S', 'F', ...])
{
  "AID": 7659597,
  "W": 795021.25,
  ...
}
[SENT] [CMD] xt%EmpireEx_25%pin%1 (Ping)
>
```

### REPL commands / Comandos del REPL

EN: In addition to raw protocol commands, the REPL accepts a few local commands that are handled before anything is sent to the game:

ES: Ademas de comandos crudos del protocolo, el REPL acepta algunos comandos locales que se manejan antes de enviar nada al juego:

| Command | Effect (EN) | Efecto (ES) |
|---|---|---|
| `/full` or `/full on` | Disable JSON truncation. Full payload printed. | Desactiva el truncado. Se imprime el JSON completo. |
| `/full off` | Restore 400-character preview. | Restaura el preview de 400 caracteres. |
| `/full <n>` | Custom character limit. Example: `/full 2000`. | Limite de caracteres custom. Ejemplo: `/full 2000`. |

EN: You can also set the initial mode via environment variable:

ES: Tambien podes fijar el modo inicial via variable de entorno:

```sh
GGE_DECODED_FULL=1 python -u main.py    # full JSON from startup
GGE_DECODED_MAX=2000 python -u main.py  # custom initial limit
```

---

## Architecture / Arquitectura

```text
+--------------+        native WSS         +------------------+
|   Chrome     | <-----------------------> |  Goodgame server |
|  (iframe)    |                           +------------------+
|              |
|  game WS     | <---- CDP listen/inject --+
+--------------+                           |
                                           |
+------------------------------------------+------------------+
|  Python process                                             |
|                                                             |
|  main.py                    -> REPL loop + bridge bootstrap |
|  lib/cdp_relay.py           -> CDP client (frames in/out)   |
|  lib/empire_decoder.py      -> base64 decoder + formatter   |
|  lib/gge_browser_selenium.py-> launches Chrome, wires relay |
|  lib/bridge_server.py       -> Flask HTTP bridge (REST)     |
+-------------------------------------------------------------+

+------------------------+       HTTP        +-----------------+
|  GGE tracker backend   | <---------------> |  bridge :4444   |
|  GGE tracker scrapers  |                   |  (this process) |
+------------------------+                   +-----------------+
```

EN: Python never opens its own WebSocket to Goodgame. It only observes and injects frames on Chrome's native socket.

ES: Python nunca abre su propio WebSocket a Goodgame. Solo observa e inyecta frames en el socket nativo de Chrome.

EN: **How injection works:** the game hides its WebSocket inside a module closure, so `window.socket` is `undefined`. When `Runtime.enable` is issued, the relay installs a passive hook on `WebSocket.prototype.send`. The next time the game sends any frame (for example the periodic `pin`), the hook registers the instance in `window.__gge_ws_list`. From that point on, `send_to_game()` picks the socket whose URL contains the configured `game_domain` and calls `.send(payload)` on it. No polling, no `queryObjects`, no cross-origin issues.

ES: **Como funciona la inyeccion:** el juego esconde su WebSocket dentro de un closure de modulo, asi que `window.socket` es `undefined`. Cuando se emite `Runtime.enable`, el relay instala un hook pasivo en `WebSocket.prototype.send`. La proxima vez que el juego envia cualquier frame (por ejemplo el `pin` periodico), el hook registra la instancia en `window.__gge_ws_list`. Desde ahi, `send_to_game()` elige el socket cuya URL contiene el `game_domain` configurado y llama `.send(payload)` sobre el. Sin polling, sin `queryObjects`, sin problemas de cross-origin.

---

## Sending commands / Enviando comandos

EN: At the `>` prompt, type any raw Empire protocol command. It is sent to the game via `Runtime.evaluate` calling `.send()` on the captured game socket (see Architecture above). Example:

ES: En el prompt `>`, escribe cualquier comando crudo del protocolo Empire. Se envia al juego via `Runtime.evaluate` llamando `.send()` sobre el socket capturado del juego (ver Arquitectura arriba). Ejemplo:

```text
> %xt%EmpireEx_25%cra%1%{"SX":738,"SY":250,"TX":737,"TY":251,"KID":0,"LID":3,...}
[SENT] [CMD] xt%EmpireEx_25%cra%1 (cra) (dict keys=['SX', 'SY', 'TX', ...])
{
  "SX": 738,
  ...
}
[RECV] [CMD] xt%EmpireEx_25%cra%1 (cra) (dict keys=['...'])
```

EN: Every frame received from the server is printed as `[RECV] [CMD] <header> (<CommandName>) <summary>`. Every frame sent by the client (either you or the game itself) is printed as `[SENT] [CMD] ...`. The raw untouched payloads are written to `/tmp/gge_raw.log` for offline analysis.

ES: Cada frame recibido del servidor se imprime como `[RECV] [CMD] <header> (<NombreComando>) <summary>`. Cada frame enviado por el cliente (sea vos o el juego mismo) se imprime como `[SENT] [CMD] ...`. Los payloads crudos sin tocar se escriben a `/tmp/gge_raw.log` para analisis offline.

EN: The base64-wrapped EmpireEx variant (frames starting with `JXh0`, which is `%xt` encoded) is decoded automatically. The terminal shows a preview of the decoded JSON; the full decoded text is written to `/tmp/gge_decoded.log`.

ES: La variante EmpireEx envuelta en base64 (frames que empiezan con `JXh0`, que es `%xt` codificado) se decodifica automaticamente. La terminal muestra un preview del JSON decodificado; el texto completo decodificado se escribe a `/tmp/gge_decoded.log`.

---

## Decoded logs / Logs decodificados

EN: Two log files are produced per session:

ES: Se producen dos archivos de log por sesion:

| File | Contents (EN) | Contenido (ES) |
|---|---|---|
| `/tmp/gge_raw.log` | Every frame exactly as it crossed the wire, base64 included. | Cada frame tal cual cruzo el cable, base64 incluido. |
| `/tmp/gge_decoded.log` | Every base64 blob expanded to its decoded text. Never truncated. | Cada blob base64 expandido a texto. Nunca truncado. |

EN: Use `gge_decoded.log` for offline parsing. It is a plain text file with one frame per section, separated by `=== <direction> (<n> bytes) ===` headers.

ES: Usa `gge_decoded.log` para parsear offline. Es un archivo de texto plano con un frame por seccion, separados por headers `=== <direction> (<n> bytes) ===`.

EN: Both files are rotated on startup: if they exceed 50 MB, they are renamed with a timestamp suffix (e.g. `gge_raw.log.20261008_143000`) instead of being truncated or appended forever.

ES: Ambos archivos se rotan al arrancar: si superan los 50 MB, se renombran con sufijo de timestamp (ej. `gge_raw.log.20261008_143000`) en vez de truncarse o crecer indefinidamente.

---

## Events log / Log de eventos

EN: A third file, `/tmp/gge_events.log`, is a **replayable timeline of player actions**. Unlike the other two logs, this one is filtered: it records only frames the client sent that were triggered by a user action. Heartbeats (`pin`) and auto UI refreshes (`gui`) are excluded, and server replies are never written here.

ES: Un tercer archivo, `/tmp/gge_events.log`, es una **linea de tiempo reproducible de acciones del jugador**. A diferencia de los otros dos logs, este va filtrado: registra solo los frames que el cliente mando disparados por una accion del usuario. Se excluyen los heartbeats (`pin`) y los auto-refresh de UI (`gui`), y las respuestas del servidor nunca se escriben aca.

### Format / Formato

```text
[YYYY-MM-DD HH:MM:SS] [SENT] [<cmd>] <full decoded frame>
```

Example / Ejemplo:

```text
[2026-10-08 12:30:11] [SENT] [bup] %xt%EmpireEx_25%bup%1%{"LID":0,"WID":228,"AMT":190,"PO":-1,"PWR":0,"SK":73,"SID":0,"AID":7659597}
[2026-10-08 12:30:14] [SENT] [cra] %xt%EmpireEx_25%cra%1%{"SX":738,"SY":250,"TX":737,"TY":251,"KID":0,"LID":3,...}
[2026-10-08 12:30:22] [SENT] [bup] %xt%EmpireEx_25%bup%1%{"LID":3,"WID":228,"AMT":70,...}
```

### Why this matters / Por que importa

EN: Every line in `gge_events.log` is a **ready-to-replay frame**. Copy everything after the second `]` (starting from `%xt%`) and paste it at the `>` prompt, and the game executes that exact action again. That turns the log into a script:

- **Replay:** re-send the frames in order to reproduce a full session.
- **Automation:** parse the file, generate variants (change commander, coordinates, troop counts) and build a bot in an afternoon.
- **Live protocol documentation:** every command the client sends, with its exact fields, is recorded. After enough clicks you have the protocol mapped empirically instead of guessing.

ES: Cada linea en `gge_events.log` es un **frame listo para reproducir**. Copia todo lo que va despues del segundo `]` (empezando desde `%xt%`) y pegalo en el prompt `>`, y el juego ejecuta esa accion exacta de nuevo. Eso convierte el log en un script:

- **Replay:** reenviar los frames en orden reproduce una sesion completa.
- **Automatizacion:** parsear el archivo, generar variantes (cambiar comandante, coordenadas, cantidad de tropas) y armar un bot en una tarde.
- **Documentacion viva del protocolo:** cada comando que el cliente manda, con sus campos exactos, queda registrado. Con suficientes clics tenes el protocolo mapeado empiricamente en vez de adivinar.

### The `EmpireEx_<n>` header / El header `EmpireEx_<n>`

EN: The number after `EmpireEx_` (e.g. `EmpireEx_25`) is the **game server identifier**, not a session token. It maps to the zone you are connected to (`EmpireEx_25` is `his1`, for example). It does **not** change between logins or reconnects as long as you stay on the same server. A frame saved today will still work tomorrow against the same server, byte for byte.

If you switch servers (log into a different zone), the number changes and any frame you replay must be updated accordingly. The current value is visible in every `[RECV]` frame on the terminal and in `/tmp/gge_decoded.log`.

ES: El numero despues de `EmpireEx_` (ej. `EmpireEx_25`) es el **identificador del servidor de juego**, no un token de sesion. Corresponde a la zona a la que estas conectado (`EmpireEx_25` es `his1`, por ejemplo). **No** cambia entre logins ni reconexiones mientras sigas en el mismo servidor. Un frame guardado hoy sigue funcionando manana contra el mismo servidor, byte por byte.

Si cambias de servidor (logueas a otra zona), el numero cambia y cualquier frame que reproduzcas tiene que actualizarse en consecuencia. El valor actual se ve en cada frame `[RECV]` en la terminal y en `/tmp/gge_decoded.log`.

### Watching it live / Verlo en vivo

EN: Open a second terminal and run:

ES: Abri una segunda terminal y corre:

```sh
tail -f /tmp/gge_events.log
```

EN: Play the game normally. Every click that produces a network request appears in that terminal in real time, clean and filtered.

ES: Juga el juego normalmente. Cada clic que produce una peticion de red aparece en esa terminal en tiempo real, limpio y filtrado.

---

## HTTP Bridge / Puente HTTP

EN: `lib/bridge_server.py` exposes an `empire-api`-compatible REST API on top of the CDP relay. Any consumer that already speaks to `empire-api` (a backend, a scraper, a Postman collection) can point at the bridge instead and get full session context, because the frames are injected into a real Chrome session that is already logged into the game.

ES: `lib/bridge_server.py` expone una API REST compatible con `empire-api` sobre el relay CDP. Cualquier consumidor que ya hable con `empire-api` (un backend, un scraper, una coleccion de Postman) puede apuntar al puente y obtener contexto de sesion completo, porque los frames se inyectan en una sesion real de Chrome que ya esta logueada al juego.

### Why it matters / Por que importa

EN: The public `empire-api` fork works with anonymous WebSocket sessions. Commands that require a session in the world (any interaction with the map, with a castle's interior, or with events) **time out** against it:

| Command | Public empire-api | This bridge |
|---|---|---|
| `hgh` (rankings) | works | works |
| `gdi` (player info) | works | works |
| `ain` (alliance info) | works | works |
| `jca` (castle analysis) | **timeout** | **works** |
| `gaa` (map areas: dungeons, storm) | **timeout** | **works** |
| `gpi` (own player info) | **404** | **works** |

ES: El fork publico de `empire-api` funciona con sesiones WebSocket anonimas. Los comandos que requieren una sesion en el mundo (cualquier interaccion con el mapa, con el interior de un castillo, o con eventos) **dan timeout** contra el:

| Comando | empire-api publico | Este puente |
|---|---|---|
| `hgh` (rankings) | funciona | funciona |
| `gdi` (info de jugador) | funciona | funciona |
| `ain` (info de alianza) | funciona | funciona |
| `jca` (castle analysis) | **timeout** | **funciona** |
| `gaa` (map areas: dungeons, storm) | **timeout** | **funciona** |
| `gpi` (info del jugador propio) | **404** | **funciona** |

### Endpoints / Endpoints

EN: The bridge mirrors the `empire-api` URL shape: `GET /<zone>/<command>/<params>`. `<params>` is the exact JSON body, URL-encoded, minus the outer braces (same as `empire-api`). Examples:

ES: El puente refleja la forma de URL de `empire-api`: `GET /<zone>/<command>/<params>`. `<params>` es el cuerpo JSON exacto, URL-encoded, sin las llaves externas (igual que `empire-api`). Ejemplos:

```sh
# Health check
curl -s 'http://localhost:4444/'

# Rankings (highscore)
curl -s 'http://localhost:4444/EmpireEx_25/hgh/"LT":6,"LID":1,"SV":"1"'

# Player info
curl -s 'http://localhost:4444/EmpireEx_25/gdi/"PID":8105340'

# Castle analysis (this is the one that fails against public empire-api)
curl -s 'http://localhost:4444/EmpireEx_25/jca/"CID":8020182,"KID":0'

# Map area (dungeons / storm)
curl -s 'http://localhost:4444/EmpireEx_25/gaa/"KID":2,"AX1":0,"AY1":0,"AX2":100,"AY2":100'
```

### Response format / Formato de respuesta

EN: Responses are wrapped in the same envelope `empire-api` uses:

```json
{
  "server": "EmpireEx_25",
  "command": "<answered-as command>",
  "return_code": 0,
  "content": { ... }
}
```

ES: Las respuestas se envuelven en el mismo sobre que usa `empire-api`:

```json
{
  "server": "EmpireEx_25",
  "command": "<comando respondido>",
  "return_code": 0,
  "content": { ... }
}
```

EN: When the request command and the response command differ, `ANSWERED_AS` maps them (same map `empire-api` uses; currently `jca` -> `jaa`). On timeout, the bridge answers HTTP 504 with `return_code: -1` and the original `response_headers`, so the consumer can retry.

ES: Cuando el comando pedido y el comando de respuesta difieren, `ANSWERED_AS` los mapea (mismo mapa que usa `empire-api`; actualmente `jca` -> `jaa`). En timeout, el puente responde HTTP 504 con `return_code: -1` y los `response_headers` originales, para que el consumidor pueda reintentar.

### How a request flows / Como viaja una peticion

```text
GET /EmpireEx_25/jca/"CID":8020182,"KID":0
  -> bridge parses zone=EmpireEx_25, cmd=jca, body={"CID":8020182,"KID":0}
  -> builds raw frame: %xt%EmpireEx_25%jca%1%{"CID":8020182,"KID":0}%
  -> relay.send_to_game(frame) via Runtime.evaluate on the hooked WS
  -> Chrome sends the frame over the native WS to Goodgame
  -> Goodgame responds with %xt%...jaa%1%{...}%
  -> CDP emits Network.webSocketFrameReceived
  -> decoder parses cmd="jaa", body={...}
  -> decoder notifies bridge.handle_response("jaa", body)
  -> the pending Event is set, HTTP handler wakes up
  -> HTTP 200 with { server, command: "jaa", return_code: 0, content: body }
```

### Wiring a consumer / Conectando un consumidor

EN: Point `GGE_API_URL` and `GGE_API_URL_REALTIME` at the bridge instead of `empire-api`:

ES: Apunta `GGE_API_URL` y `GGE_API_URL_REALTIME` al puente en vez de a `empire-api`:

```env
# When the consumer runs in Docker and the bridge runs on the host,
# use the docker bridge gateway IP:
GGE_API_URL=http://172.19.0.1:4444
GGE_API_URL_REALTIME=http://172.19.0.1:4444
```

EN: Get the gateway IP with:

ES: Obtene la IP del gateway con:

```sh
docker network inspect backend --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
```

EN: If the consumer runs on the same host (not in Docker), use `http://localhost:4444` directly.

ES: Si el consumidor corre en el mismo host (no en Docker), usa `http://localhost:4444` directamente.

### Constraints / Restricciones

EN: The bridge currently does **not** pipeline concurrent requests for the same response command. Since EmpireEx frames have no request id, the bridge cannot tell two in-flight `jca` requests apart. A second request for the same answered-as command while one is pending gets HTTP 429. In practice this is fine: the tracker scrapers are single-threaded per server.

ES: El puente actualmente **no** pipelina peticiones concurrentes para el mismo comando de respuesta. Como los frames EmpireEx no traen request id, el puente no puede distinguir dos `jca` en vuelo. Una segunda peticion para el mismo comando respondido mientras hay una pendiente devuelve HTTP 429. En la practica no molesta: los scrapers del tracker son monohilo por servidor.

EN: **Chrome must stay open and logged in.** If Chrome closes, if the session expires, or if the game tab is closed, every request through the bridge will time out until Chrome is reopened and re-logged.

ES: **Chrome tiene que quedar abierto y logueado.** Si Chrome se cierra, si la sesion expira, o si la pestaña del juego se cierra, toda peticion a traves del puente va a dar timeout hasta que se reabra Chrome y se vuelva a loguear.

---

## Files / Archivos

| File | Purpose (EN) | Proposito (ES) |
|---|---|---|
| `main.py` | Entry point and REPL loop, starts the bridge | Punto de entrada y bucle REPL, arranca el puente |
| `lib/cdp_relay.py` | Chrome DevTools Protocol client | Cliente del Chrome DevTools Protocol |
| `lib/empire_decoder.py` | EmpireEx base64 decoder and formatter | Decodificador base64 y formateador EmpireEx |
| `lib/gge_browser_selenium.py` | Launches Chrome, wires the relay | Lanza Chrome y conecta el relay |
| `lib/bridge_server.py` | Flask HTTP bridge (`empire-api` compatible) | Puente HTTP Flask (compatible con `empire-api`) |
| `lib/gge_socket_browser.py` | Legacy callback container | Contenedor de callbacks legado |
| `lib/websocket_server.py` | Legacy WS proxy (unused) | Proxy WS legado (no usado) |
| `lib/colors.py` | ANSI color codes | Codigos ANSI de color |

Runtime artifacts (not part of the repository / no forman parte del repositorio):

| File | Purpose (EN) | Proposito (ES) |
|---|---|---|
| `/tmp/gge_raw.log` | Raw frames, never truncated | Frames crudos, nunca truncados |
| `/tmp/gge_decoded.log` | Base64 expanded to text | Base64 expandido a texto |
| `/tmp/gge_events.log` | Replayable player actions only | Solo acciones reproducibles del jugador |
| `user-data/` | Chrome profile (session cookies) | Perfil de Chrome (cookies de sesion) |

---

## Troubleshooting / Solucion de problemas

**EN: `google-chrome not found`**

Install Google Chrome. On Arch-based distros, use the AUR:

**ES: `google-chrome not found`**

Instala Google Chrome. En distros basadas en Arch, usa el AUR:

```sh
yay -S google-chrome
```

---

**EN: `Handshake status 403 Forbidden` when connecting to CDP**

Chrome 111+ requires the `--remote-allow-origins=*` flag AND `suppress_origin=True` on the client. Both are already set in this fork.

**ES: `Handshake status 403 Forbidden` al conectar al CDP**

Chrome 111+ requiere la flag `--remote-allow-origins=*` Y `suppress_origin=True` en el cliente. Ambas ya estan configuradas en este fork.

---

**EN: `Handshake status 500 ... No such target id: <id>`**

The iframe navigated internally between the moment the target was discovered and the moment the WebSocket connection was attempted. The target id found on the first poll was destroyed and replaced by a new one. This is transient: the relay retries on its own (up to 6 times with a 0.5s delay). If it persists after the retries, the game tab probably reloaded; refresh it manually.

**ES: `Handshake status 500 ... No such target id: <id>`**

El iframe navego internamente entre el momento en que se descubrio el target y el momento en que se intento la conexion WebSocket. El target id encontrado en el primer intento fue destruido y reemplazado por uno nuevo. Es transitorio: el relay reintenta solo (hasta 6 veces con 0.5s de delay). Si persiste despues de los reintentos, probablemente la pestaña del juego se recargo; refrescala a mano.

---

**EN: `unable to discover open window in chrome`**

Chrome left a locked `user-data/` directory behind. Clean up:

**ES: `unable to discover open window in chrome`**

Chrome dejo un directorio `user-data/` bloqueado. Limpia:

```sh
pkill -9 -f chrome
rm -rf user-data/
```

---

**EN: Game stuck at "Sharpening swords" / login screen never loads**

The relay did not connect. Check `/tmp/gge_raw.log` and the DevTools console of the `index.html` iframe.

**ES: Juego atascado en "Afilando las espadas" / login nunca carga**

El relay no conecto. Revisa `/tmp/gge_raw.log` y la consola de DevTools del iframe `index.html`.

---

**EN: Commands typed at `>` produce no `[SENT]` and no `[RECV]`**

The passive WebSocket hook has not captured the game socket yet. This is normal during the first seconds after connecting: the hook only fires when the game sends its next frame (usually the periodic `pin`). Solutions:

- Wait a few seconds and try again.
- Or reload the game tab (`F5`). The relay reinstalls the hook and the game immediately sends a fresh frame.

You can verify the capture worked by looking for:

```text
[CDP] Runtime.evaluate id=X -> OK i=0 list=1 url=wss://...goodgamestudios.com/
```

If instead you see `NO_WS_YET list=0 []`, the hook has not captured anything yet.

**ES: Los comandos en `>` no producen `[SENT]` ni `[RECV]`**

El hook pasivo del WebSocket todavia no capturo el socket del juego. Esto es normal durante los primeros segundos tras conectar: el hook solo se dispara cuando el juego envia su proximo frame (usualmente el `pin` periodico). Soluciones:

- Espera unos segundos e intenta de nuevo.
- O recarga la pestaña del juego (`F5`). El relay reinstala el hook y el juego envia un frame fresco inmediatamente.

Podes verificar que la captura funciono buscando:

```text
[CDP] Runtime.evaluate id=X -> OK i=0 list=1 url=wss://...goodgamestudios.com/
```

Si en cambio ves `NO_WS_YET list=0 []`, el hook todavia no capturo nada.

---

**EN: Bridge returns `{"error": "Timeout", "return_code": -1}`**

The bridge sent the frame but no matching `RECV` arrived within `timeout` seconds. Common causes:

1. **Session expired in Chrome.** Re-login in the Chrome tab. The relay stays connected but the server rejects commands.
2. **The `CID` belongs to a different kingdom.** Castle ids (`CID`) are kingdom-specific. `jca/"CID":X,"KID":0` and `jca/"CID":X,"KID":2` are two different castles; use the one the game shows when you click the castle in question.
3. **Command requires a state you are not in.** For example, `gaa` on a kingdom the current session has not entered will not answer until you enter it manually in the browser once.

**ES: El puente devuelve `{"error": "Timeout", "return_code": -1}`**

El puente envio el frame pero no llego ningun `RECV` que matchee dentro de `timeout` segundos. Causas comunes:

1. **Sesion expirada en Chrome.** Volve a loguearte en la pestaña de Chrome. El relay sigue conectado pero el servidor rechaza los comandos.
2. **El `CID` pertenece a otro reino.** Los ids de castillo (`CID`) son especificos por reino. `jca/"CID":X,"KID":0` y `jca/"CID":X,"KID":2` son dos castillos distintos; usa el que el juego muestra cuando haces clic en el castillo en cuestion.
3. **El comando requiere un estado en el que no estas.** Por ejemplo, `gaa` sobre un reino al que la sesion actual no entro no va a responder hasta que entres manualmente una vez desde el navegador.

---

**EN: Bridge returns `{"error": "Relay not ready (Chrome not logged in yet)"}`**

The bridge is up but the CDP relay has not connected yet. Wait for `[PY] CDP relay active.` in the terminal. If it never appears, see the "Game stuck" section above.

**ES: El puente devuelve `{"error": "Relay not ready (Chrome not logged in yet)"}`**

El puente esta arriba pero el relay CDP todavia no conecto. Espera a `[PY] CDP relay active.` en la terminal. Si nunca aparece, mira la seccion "Juego atascado" arriba.

---

**EN: Bridge returns HTTP 429 `{"error": "Another request for this command is in flight"}`**

The consumer is sending two concurrent requests for the same response command. Serialize them, or give the bridge a bigger `timeout` so the first one finishes before the second starts.

**ES: El puente devuelve HTTP 429 `{"error": "Another request for this command is in flight"}`**

El consumidor esta mandando dos peticiones concurrentes para el mismo comando de respuesta. Serializalas, o dale al puente un `timeout` mas grande para que la primera termine antes de que arranque la segunda.

---

## Platform notes / Notas de plataforma

EN: The current code was developed and tested on Linux. macOS works out of the box. Windows works but needs three small adjustments:

**1. Hardcoded `/tmp/` paths.** `lib/empire_decoder.py` writes to `/tmp/gge_raw.log`, `/tmp/gge_decoded.log` and `/tmp/gge_events.log`. On Windows `/tmp/` does not exist. Either create `C:\tmp\` manually, or patch the constants at the top of the file:

```python
import tempfile
_TMP = tempfile.gettempdir()
RAW_LOG = _TMP + "/gge_raw.log"
DECODED_LOG = _TMP + "/gge_decoded.log"
EVENTS_LOG = _TMP + "/gge_events.log"
```

**2. `readline` module.** `main.py` and `lib/gge_browser_selenium.py` import `readline`. Python's standard library does not ship `readline` on Windows. Install the drop-in replacement:

```sh
pip install pyreadline3
```

`pyreadline3` registers itself under the `readline` name, so `import readline` keeps working unchanged.

**3. Troubleshooting commands.** The `pkill -9 -f chrome` and `rm -rf user-data/` snippets in the Troubleshooting section are Unix-only. Windows equivalents:

```powershell
taskkill /F /IM chrome.exe
rmdir /S /Q user-data
```

ES: El codigo actual fue desarrollado y probado en Linux. macOS funciona sin cambios. Windows funciona pero necesita tres ajustes chicos:

**1. Rutas `/tmp/` hardcodeadas.** `lib/empire_decoder.py` escribe a `/tmp/gge_raw.log`, `/tmp/gge_decoded.log` y `/tmp/gge_events.log`. En Windows `/tmp/` no existe. O creas `C:\tmp\` a mano, o parcheas las constantes al inicio del archivo (mismo snippet de arriba).

**2. Modulo `readline`.** `main.py` y `lib/gge_browser_selenium.py` importan `readline`. La libreria estandar de Python no incluye `readline` en Windows. Instala el reemplazo directo:

```sh
pip install pyreadline3
```

`pyreadline3` se registra bajo el nombre `readline`, asi que `import readline` sigue funcionando sin cambios.

**3. Comandos de troubleshooting.** Los snippets `pkill -9 -f chrome` y `rm -rf user-data/` de la seccion Troubleshooting son solo-Unix. Equivalentes en Windows:

```powershell
taskkill /F /IM chrome.exe
rmdir /S /Q user-data
```

EN: **Linux-only features:** none. The hook mechanism, CDP relay, decoder, HTTP bridge and REPL all work identically on every platform once the adjustments above are applied.

ES: **Funciones solo-Linux:** ninguna. El mecanismo del hook, el relay CDP, el decoder, el puente HTTP y el REPL funcionan igual en cualquier plataforma una vez aplicados los ajustes de arriba.

---

## Security / Seguridad

EN: This fork does not use `--disable-web-security`. Chrome talks to Goodgame with its own TLS stack and normal security policies. The `user-data/` directory is a separate Chrome profile used only by this tool; do not use it for regular browsing.

ES: Este fork no usa `--disable-web-security`. Chrome habla con Goodgame con su propio stack TLS y politicas de seguridad normales. El directorio `user-data/` es un perfil de Chrome separado usado solo por esta herramienta; no lo uses para navegar normalmente.

**EN: Never commit `user-data/`.** It contains session cookies for your Goodgame account.

**ES: Nunca hagas commit de `user-data/`.** Contiene cookies de sesion de tu cuenta de Goodgame.

**EN: The HTTP bridge binds to `0.0.0.0` by default.** If the host is reachable from an untrusted network, anyone on that network can inject commands into your game session. Bind to `127.0.0.1` if you only need local access, or firewall the port.

**ES: El puente HTTP se bindea a `0.0.0.0` por defecto.** Si el host es alcanzable desde una red no confiable, cualquiera en esa red puede inyectar comandos en tu sesion de juego. Bindea a `127.0.0.1` si solo necesitas acceso local, o bloquea el puerto en el firewall.

**EN: Terms of Service.** Goodgame Studios' ToS prohibit automation, bots, and external tools that interact with the game. This project is provided for educational and interoperability research purposes only. Using it on a live account may result in warnings, temporary suspension or a permanent ban. You assume all risk.

**ES: Terminos de Servicio.** Los ToS de Goodgame Studios prohiben la automatizacion, los bots y las herramientas externas que interactuen con el juego. Este proyecto se provee solo con fines educativos y de investigacion de interoperabilidad. Usarlo en una cuenta activa puede resultar en advertencias, suspension temporal o ban permanente. Asumis todo el riesgo.

---

## Credits / Creditos

EN: Original project by [danadum](https://github.com/danadum). Chrome 155+ compatibility (CDP relay), EmpireEx decoder, passive WebSocket hook and HTTP bridge added by [Synapse-VE](https://github.com/Synapse-VE).

EN: The HTTP bridge is designed to be compatible with [gge-tracker](https://github.com/gge-tracker/gge-tracker) — the public tracker project for Goodgame Empire. Pointing its `GGE_API_URL` at this bridge unlocks commands (`jca`, `gaa`, `gpi`) that time out against the public `empire-api` fork.

ES: Proyecto original de [danadum](https://github.com/danadum). Compatibilidad con Chrome 155+ (relay CDP), decoder EmpireEx, hook pasivo del WebSocket y puente HTTP agregados por [Synapse-VE](https://github.com/Synapse-VE).

ES: El puente HTTP esta diseñado para ser compatible con [gge-tracker](https://github.com/gge-tracker/gge-tracker) — el proyecto publico de tracker para Goodgame Empire. Apuntar su `GGE_API_URL` a este puente desbloquea comandos (`jca`, `gaa`, `gpi`) que dan timeout contra el fork publico de `empire-api`.

---

## License / Licencia

EN: Same license as the original project.

ES: Misma licencia que el proyecto original.