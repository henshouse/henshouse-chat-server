# region imports
from threading import Thread
from time import sleep
import os
import signal
import sys
import asyncio
from typing import Union
import websockets as ws

from constants import NAME_SPLITTER, VERSION, PORT
from connection import Connection
from security import Asymmetric
from log import log_start, log
# endregion


class Server:
    def __init__(self, ip: str, port: int, max_conn: int = -1):
        self.ip = ip
        self.port = port
        self.addr = (self.ip, self.port)
        self.max_conn = max_conn

        self.running = True
        self.conns = []

        self.local_asym = Asymmetric.new()

        log_start()
        asyncio.run(self.run_server())

    def start_exit_thread(self):
        def quit_thread():
            try:
                while True:
                    cmd = input('').lower()
                    if cmd in ('q', 'quit', ':q', ':q!', 'exit'):
                        os.kill(os.getpid(), signal.SIGINT)
                    elif cmd == 'help':
                        print(
                            f'> enter any of "q", "quit", ":q", ":q!" or "exit" and press enter to quit')
                    else:
                        print(f'[!] Command unknown')
            except EOFError:
                os.kill(os.getpid(), signal.SIGINT)
        Thread(target=quit_thread).start()

    async def run_server(self):
        n = 1

        async def new_conn(wsock: ws.WebSocketServerProtocol):
            nonlocal n
            nick = str(n)
            n += 1
            conn = Connection(wsock, wsock.remote_address[0], self, nick)
            self.conns.append(conn)
            await conn.run()

        self.start_exit_thread()

        log(f'Server Running')
        log(f'Listening on port {self.port}')

        try:
            async with ws.serve(new_conn, self.ip, self.port):
                await asyncio.Future()
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            log(e)

    async def send_to_all(self, msg, author: Union[Connection, str]):
        msg = (author.nick if isinstance(author, Connection)
               else author) + NAME_SPLITTER + msg
        to_remove = []
        for conn in self.conns:
            msg_with_me = conn.nick + NAME_SPLITTER + msg
            try:
                await conn.send_str_sym(msg_with_me)
            except ws.exceptions.ConnectionClosedOK:
                to_remove.append(conn)
        for conn in to_remove:
            if conn in self.conns:
                self.conns.remove(conn)
            await conn.close()

    async def send_to_all_raw(self, msg, author: Union[Connection, str]):
        msg = (author.nick if isinstance(author, Connection)
               else author) + NAME_SPLITTER + msg
        to_remove = []
        for conn in self.conns:
            msg_with_me = conn.nick + NAME_SPLITTER + msg
            try:
                await conn.send(msg_with_me)
            except ws.exceptions.ConnectionClosedOK:
                to_remove.append(conn)
        for conn in to_remove:
            if conn in self.conns:
                self.conns.remove(conn)
            await conn.close()


def get_ip():
    import socket as sc
    sock = sc.socket(sc.AF_INET, sc.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    server = sock.getsockname()[0]
    sock.close()
    sleep(0.5)
    return server


def run():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(f'--port', type=int,
                        help='port number for server, defaults to {PORT}')
    parser.add_argument(f'--version', action='store_true',
                        help='print version and exit')
    args = parser.parse_args()
    if args.version:
        print(f'Version: {VERSION}')
        sys.exit()
    if args.port is not None:
        _port = args.port
    else:
        _port = PORT
    # _ip = '10.0.1.17'
    log(f'You are running version {VERSION}')

    _ip = get_ip()

    log(f"Running on {(_ip, _port)}")
    Server(_ip, _port)


def test_server():
    import asyncio
    import websockets

    async def echo(websocket):
        async for message in websocket:
            await websocket.send(message)

    async def main():
        async with websockets.serve(echo, "localhost", 8765):
            await asyncio.Future()  # run forever

    asyncio.run(main())


if __name__ == '__main__':
    run()
