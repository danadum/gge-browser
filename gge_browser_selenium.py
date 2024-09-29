from websocket_server import WebsocketServer

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

import json
import threading
import _thread
import sys
import traceback

def open_browser(game_url, on_ready):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    driver.get(game_url)
    iframe = start_game(driver, on_ready)
    threading.Thread(target=watch_reload, args=(driver, iframe, on_ready), daemon=True).start()

def start_game(webdriver, on_ready):
    webdriver.set_network_conditions(offline=True, latency=1000, throughput=0)
    webdriver.execute_cdp_cmd("Network.clearBrowserCache", {})
    webdriver.set_network_conditions(offline=False, latency=1000, throughput=500 * 1024)
    webdriver.refresh()
    wait = WebDriverWait(webdriver, 30, poll_frequency=0.01)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body[style*="background-image"]')))
    wait.until(EC.presence_of_element_located((By.ID, 'game')))
    iframe = webdriver.find_element(By.ID, 'game')
    webdriver.switch_to.frame(iframe)
    webdriver.execute_script(on_ready)
    webdriver.switch_to.default_content()
    webdriver.delete_network_conditions()
    return iframe

def watch_reload(webdriver, iframe, on_ready):
    while True:
        try:
            WebDriverWait(webdriver, float('inf')).until(EC.staleness_of(iframe))
            iframe = start_game(webdriver, on_ready)
        except Exception as e:
            if isinstance(e, WebDriverException) and "target frame detached" in str(e):
                pass
            elif isinstance(e, WebDriverException) and "unknown error: cannot determine loading status" in str(e):
                pass
            elif isinstance(e, WebDriverException) and "unknown error: bad inspector message" in str(e):
                pass
            else:
                traceback.print_exc()
                _thread.interrupt_main()
                sys.exit()

def connect_with_browser(ws_mock, game_url, ws_server_port):
    def on_server_message(ws, message):
        type, data = message.split('#', 1)
        if type == 'send' and ws_mock.on_send:
            ws_mock.on_send(ws_mock, data)
        elif type == 'open' and ws_mock.on_open:
            ws_mock.on_open(ws_mock)
        elif type == 'close' and ws_mock.on_close:
            close_data = json.loads(data)
            ws_mock.on_close(ws_mock, close_data.get('code', ''), close_data.get('reason', ''))
        elif type == 'error' and ws_mock.on_error:
            error_data = json.loads(data)
            ws_mock.on_error(ws_mock, error_data.get('message', ''))
        elif type == 'message' and ws_mock.on_message:
            ws_mock.on_message(ws_mock, data)
        elif type == 'log' and ws_mock.on_log:
            ws_mock.on_log(ws_mock, data)

    ws_mock.ws_server = WebsocketServer(ws_server_port,on_message=on_server_message)
    threading.Thread(target=ws_mock.ws_server.start_sync, daemon=True).start()

    on_ready = """
        window.sockets = [];

        const localSocket = new WebSocket('ws://localhost:%i');
        localSocket.addEventListener('message', async (event) => {
            let data = await event.data;
            window.sockets.forEach(socket => socket.send(data));
        });

        const originalWebSocket = window.WebSocket;
        window.WebSocket = class extends originalWebSocket {
            constructor(url, protocols) {
                localSocket.send(`log#Websocket url: ${url}`);             
                super(url, protocols);
                window.sockets.push(this);

                this.addEventListener('open', event => {
                    localSocket.send(`open#`);
                });

                this.addEventListener('close', event => {
                    localSocket.send(`close#${JSON.stringify({code: event.code, reason: event.reason})}`);
                    window.sockets = window.sockets.filter(socket => socket !== this);
                });

                this.addEventListener('error', event => {
                    localSocket.send(`error#${JSON.stringify({message: event.data})}`);
                });

                Object.defineProperty(this, "onmessage", {
                    set(fn) {
                        this.original_onmessage = fn;
                        return this.addEventListener('message', async (event) => {
                            let data = await event.data.text();
                            localSocket.send(`message#${data}`);
                            fn(event);
                        });
                    }
                });
            }

            send(data) {
                localSocket.send(`send#${data}`);
                super.send(data);
            }
        };
    """ % ws_server_port

    open_browser(game_url, on_ready)
