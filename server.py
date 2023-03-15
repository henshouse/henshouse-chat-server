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
from log import log_message, log_start, log
import config as cfg

# endregion


class ServerFakeConn:
    def __init__(self):
        self.nick = "[SERVER]"
        self.id = 0


class Server:
    def __init__(self, ip: str, port: int, max_conn: int = -1):
        self.ip = ip
        self.port = port
        self.addr = (self.ip, self.port)
        self.max_conn = max_conn

        self.running = True
        self.conns: list[Connection] = []
        self.self_connection = ServerFakeConn()

        self.local_asym = Asymmetric.new()

        log_start()
        asyncio.run(self.run())

    async def run_command(self, sender: Connection, cmd: str, args: str) -> bool:
        if cmd == "nick":
            old_nick = sender.nick
            nick = args.split(" ")[0]
            if len(nick) == 0:
                await sender.send_message("Nick reseted", self.self_connection)
                sender.nick = sender.get
                await self.send_msg_to_all(
                    self.to_msg_by_server(f"{old_nick} changed nick to {sender.nick}"),
                    self.self_connection,
                )
                log_message(
                    self.self_connection.nick,
                    self.self_connection.nick,
                    f"{old_nick} changed nick to {sender.nick}",
                )
                return
            if len(nick) > 64:
                await sender.send_message(
                    "Nick too long (max 64)", self.self_connection
                )
                return

            sender.nick = args.split(" ")[0]
            await self.send_msg_to_all(
                self.to_msg_by_server(f"{old_nick} changed nick to {sender.nick}"),
                self.self_connection,
            )
            log_message(
                self.self_connection.nick,
                self.self_connection.nick,
                f"{old_nick} changed nick to {sender.nick}",
            )
            return True
        
    async def notify_login(self, conn: Connection):
        await self.send_msg_to_all(
            self.to_msg_by_server(f"{conn.nick} connected"), self.self_connection
        )

    async def run(self):
        async def new_conn(wsock: ws.WebSocketServerProtocol):
            conn = Connection(wsock, wsock.remote_address[0], self)
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

    def to_msg_by_server(self, msg: str) -> FromServerMessage:
        return {
            "type": "message",
            "content": msg,
            "author": self.self_connection.nick,
            "author_id": 0,
        }

    async def send_close(self, conn: Connection):
        await self.send_msg_to_all(
            self.to_msg_by_server(f"{conn.nick} disconnected"), self.self_connection
        )

    async def send_msg_to_all(
        self, msg: FromServerMessage, author: Union[Connection, str]
    ):
        to_remove: list[Connection] = []
        for conn in self.conns:
            local_msg = msg.copy()
            local_msg["recipient"] = conn.nick
            local_msg["recipient_id"] = conn.id

            try:
                await conn.resend_message(local_msg, author)
            except ws.ConnectionClosedOK:
                to_remove.append(conn)
            except ws.ConnectionClosedError:
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
                    if cmd in ("q", "quit", ":q", ":q!", "exit", "stop"):
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
