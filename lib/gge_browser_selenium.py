import threading
import traceback
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

from lib.websocket_server import WebsocketServer


def open_browser(game_url, on_ready):
    port = 9222
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={os.path.join(os.getcwd(), 'user-data')}")
    options.add_argument(f"--remote-debugging-port={port}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    print(len(driver.window_handles), "windows opened")
    exit(0)
    windows = driver.window_handles
    if len(windows) > 1:
        driver.switch_to.window(windows[0])
        driver.close()
        driver.switch_to.window(windows[1])

    driver.get(game_url)
    threading.Thread(target=watch_reload, args=(driver, on_ready), daemon=True).start()

def start_game(webdriver, on_ready):
    webdriver.set_network_conditions(offline=True, latency=1000, throughput=0)
    webdriver.execute_cdp_cmd("Network.clearBrowserCache", {})
    webdriver.set_network_conditions(offline=False, latency=1000, throughput=500 * 1024)
    webdriver.refresh()
    wait = WebDriverWait(webdriver, 30, poll_frequency=0.01)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body[style*="background-image"]')))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe#game')))
    iframe = webdriver.find_element(By.CSS_SELECTOR, 'iframe#game')
    webdriver.switch_to.frame(iframe)
    webdriver.execute_script(on_ready)
    webdriver.switch_to.default_content()
    webdriver.delete_network_conditions()
    return iframe

def watch_reload(webdriver, on_ready):
    while True:
        try:
            WebDriverWait(webdriver, float('inf')).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe#game')))
            iframe = start_game(webdriver, on_ready)
            WebDriverWait(webdriver, float('inf')).until(EC.staleness_of(iframe))
        except Exception as e:
            if isinstance(e, WebDriverException) and "target frame detached" in str(e):
                pass
            elif isinstance(e, WebDriverException) and "unknown error: cannot determine loading status" in str(e):
                pass
            elif isinstance(e, WebDriverException) and "unknown error: bad inspector message" in str(e):
                pass
            else:
                traceback.print_exc()
                break

def connect_with_browser(socket, game_url, ws_server_port):
    ws_server = WebsocketServer(
        ws_server_port,
        on_message=lambda ws, msg: socket.send(msg),
        on_connection=lambda ws: socket.open(ws.request.path.strip("/")),
        on_disconnection=lambda ws: socket.close()
    )
    socket.set_ws_server(ws_server)
    threading.Thread(target=ws_server.start_sync, daemon=True).start()

    on_ready = """
        const originalWebSocket = window.WebSocket;
        window.WebSocket = class extends originalWebSocket {
            constructor(url, protocols) {
                super(`ws://localhost:%i/${url}`, protocols);
                window.socket = this;
                this.opened = false;

                Object.defineProperty(this, "onopen", {
                    set(fn) {
                        this.original_onopen = fn;
                        return this.addEventListener('open', event => {});
                    }
                });

                Object.defineProperty(this, "onmessage", {
                    set(fn) {
                        this.original_onmessage = fn;
                        return this.addEventListener('message', event => {
                            if (this.opened) {
                                return fn(event);
                            } else {
                                this.opened = true;
                                this.original_onopen(new Event('open'));
                            }
                        });
                    }
                });
            }
        };
    """ % ws_server_port

    open_browser(game_url, on_ready)
