# region imports
from threading import Thread
from time import sleep
import os
import signal
import sys
import asyncio
from typing import Union
import websockets as ws
from hashlib import sha224

from constants import NAME_SPLITTER, VERSION, PORT
from connection import Connection, FromServerMessage
from security import Asymmetric
from log import log_start, log
import config as cfg

# endregion


class ServerFakeConn:
    def __init__(self):
        self.nick = "[SERVER]"


class Server:
    def __init__(self, ip: str, port: int, max_conn: int = -1):
        self.ip = ip
        self.port = port
        self.addr = (self.ip, self.port)
        self.max_conn = max_conn

        self.running = True
        self.conns: list[Connection] = []
        self.server_fake_conn = ServerFakeConn()

        self.local_asym = Asymmetric.new()

        log_start()
        asyncio.run(self.run())

    async def run_command(self, sender: Connection, cmd: str, args: str) -> bool:
        if cmd == "nick":
            nick = args.split(" ")[0]
            if len(nick) == 0:
                await sender._send_sym(
                    f"{sender.nick}{NAME_SPLITTER}{self.server_fake_conn.nick}{NAME_SPLITTER}Provide nick"
                )
            if len(nick) > 64:
                await sender._send_sym(
                    f"{sender.nick}{NAME_SPLITTER}{self.server_fake_conn.nick}{NAME_SPLITTER}Nick too long (max 64)"
                )
            sender.nick = args.split(" ")[0]
            return True

    async def run(self):
        n = 1

        async def new_conn(wsock: ws.WebSocketServerProtocol):
            nonlocal n
            # nick = str(hex(id(wsock)))[2:7]
            nick = sha224(str(id(wsock)).encode()).hexdigest()[:5]
            n += 1
            conn = Connection(wsock, wsock.remote_address[0], self, nick)
            self.conns.append(conn)
            await conn.run()

        self._start_exit_thread()

        log(f"Server Running")
        log(f"Listening on port {self.port}")

        try:
            async with ws.serve(new_conn, self.ip, self.port):
                await asyncio.Future()
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            log(e)

    async def send_close(self, conn: Connection):
        await self.send_msg_to_all(f"{conn.nick} disconnected", self.server_fake_conn)

    async def send_msg_to_all(
        self, msg: FromServerMessage, author: Union[Connection, str]
    ):
        to_remove: list[Connection] = []
        for conn in self.conns:
            try:
                await conn.resend_message(msg, author)
            except ws.ConnectionClosedOK:
                to_remove.append(conn)
            except ws.ConnectionClosedError:
                to_remove.append(conn)

        for conn in to_remove:
            if conn in self.conns:
                self.conns.remove(conn)
            await conn.close()

    async def send_msg_to_all_raw(self, msg, author: Union[Connection, str]):
        msg = (
            (
                author.nick
                if isinstance(author, Connection) or isinstance(author, ServerFakeConn)
                else author
            )
            + NAME_SPLITTER
            + msg
        )
        to_remove = []
        for conn in self.conns:
            msg_with_me = conn.nick + NAME_SPLITTER + msg
            try:
                await conn.send_plain(msg_with_me)
            except ws.exceptions.ConnectionClosedOK:
                to_remove.append(conn)
        for conn in to_remove:
            if conn in self.conns:
                self.conns.remove(conn)
            await conn.close()

    def _start_exit_thread(self):
        def quit_thread():
            try:
                while True:
                    cmd = input("").lower()
                    if cmd in ("q", "quit", ":q", ":q!", "exit"):
                        os.kill(os.getpid(), signal.SIGINT)
                    elif cmd == "help":
                        print(
                            f'> enter any of "q", "quit", ":q", ":q!" or "exit" and press enter to quit (on linux do it twice, it\'s bug we are working on)'
                        )
                    else:
                        print(f"[!] Command unknown")
            except EOFError:
                os.kill(os.getpid(), signal.SIGINT)

        Thread(target=quit_thread).start()


def get_ip() -> str:
    import socket as sc

    try:
        sock = sc.socket(sc.AF_INET, sc.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        server = sock.getsockname()[0]
        sock.close()
    except:
        return "localhost"
    return server
