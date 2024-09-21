from websocket_mock import WebSocketAppMock
from colors import colors

import readline
import sys


def print_preserve_input(message):
    input = readline.get_line_buffer()
    sys.stdout.write(f"\x1b[1K\r{message}\n> {input}")


if __name__ == '__main__':
    socket = WebSocketAppMock(
        "",
        on_open=lambda ws: print_preserve_input(colors.PURPLE + 'WebSocket opened' + colors.ENDC),
        on_message=lambda ws, message: print_preserve_input(colors.BLUE + message + colors.ENDC),
        on_error=lambda ws, error: print_preserve_input(colors.RED + error + colors.ENDC),
        on_close=lambda ws, close_status_code, close_msg: print_preserve_input(colors.PURPLE + f'WebSocket closed with code {close_status_code} and message {close_msg}' + colors.ENDC),
        on_send=lambda ws, message: print_preserve_input(colors.GREEN + message + colors.ENDC),
        game_url='https://danadum.github.io/empire'
    )

    socket.run_forever()
    
    while True:
        socket.send(input(">"))
