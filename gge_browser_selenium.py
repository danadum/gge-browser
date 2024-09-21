from websocket_server import WebsocketServer

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json
import threading

def open_browser(game_url, on_ready):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)

    driver.get(game_url)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'game')))
    iframe = driver.find_element(By.ID, 'game')
    driver.switch_to.frame(iframe)
    driver.execute_script(on_ready)


def connect_with_browser(ws_mock, game_url, ws_server_port):
    def on_server_message(ws, message):
        type, data = message.split('#', 1)
        if type == 'send':
            ws_mock.on_send(ws_mock, data)
        elif type == 'open':
            ws_mock.on_open(ws_mock)
        elif type == 'close':
            close_data = json.loads(data)
            ws_mock.on_close(ws_mock, close_data['code'], close_data['reason'])
        elif type == 'error':
            error_data = json.loads(data)
            ws_mock.on_error(ws_mock, error_data['message'])
        elif type == 'message':
            ws_mock.on_message(ws_mock, data)

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
            constructor(...args) {
                super(...args);

                window.sockets.push(this);
                
                this.addEventListener('message', async (event) => {
                    localSocket.send(`message#${await event.data.text()}`);
                });

                this.addEventListener('open', event => {
                    localSocket.send(`open#`);
                });

                this.addEventListener('close', event => {
                    localSocket.send(`close#${JSON.stringify({code: event.code, reason: event.reason})}`);
                    window.sockets = window.sockets.filter(socket => socket !== this);
                });

                this.addEventListener('error', event => {
                    localSocket.send(`error#$JSON.stringify({message: event.message})`);
                });
            }

            send(data) {
                localSocket.send(`send#${data}`);
                super.send(data);
            }
        };
    """ % ws_server_port

    open_browser(game_url, on_ready)
