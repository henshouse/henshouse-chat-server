from threading import Thread
import websockets as ws
import asyncio

from log import log_message, log_disconnect
from security import Symmetric, Asymmetric
from log import log_connect


class Connection:
    @staticmethod
    def new(sock, addr, server, n):
        conn = Connection(sock, addr, server, n)
        asyncio.ensure_future(conn.run())
        return conn

    def __init__(self, ws: ws.WebSocketServerProtocol, addr: str, server, nick: str):
        self.ws = ws
        self.addr = addr

        self.server = server

        self.nick = nick
        self.sym = Symmetric()

    async def send(self, msg: bytes):
        await self.ws.send(msg)

    async def recv(self) -> bytes:
        return await self.ws.recv()

    async def recv_str_asym(self) -> str:
        return self.server.local_asym.decrypt(await self.recv())

    async def send_str_asym(self, msg: str):
        return await self.send(self.remote_asym.encrypt(msg))

    async def send_en_asym(self, msg: bytes):
        return await self.send(self.remote_asym.encrypt_bytes(msg))

    async def recv_str_sym(self) -> str:
        return self.sym.decrypt(await self.recv())

    async def send_str_sym(self, msg: str):
        enc = self.sym.encrypt(msg)
        # print(f'encrypted: {enc}')
        return await self.send(enc)

    async def send_en_sym(self, msg: bytes):
        return await self.send(self.sym.encrypt_bytes(msg))

    async def close(self, error: str = None):
        await self.ws.close()
        await self.server.send_close(self)
        if error:
            log_disconnect(self.addr, self.nick, reason=f'Error: {error}')
        else:
            log_disconnect(self.addr, self.nick)

    async def run(self):
        try:
            key = self.server.local_asym.export_public()
            await self.send(key)
            self.remote_asym = Asymmetric.import_from(await self.recv())
            await self.send_en_asym(self.sym.key)
            log_connect(self.addr, self.nick)
            async for msg_en in self.ws:
                msg = self.sym.decrypt(msg_en)

                if len(msg):
                    if msg[0] == '/':
                        if len(msg[1:].split(' ')) > 0:
                            cmd_by_space = msg[1:].split(' ')
                            args = '' if len(cmd_by_space) == 1 else ' '.join(
                                cmd_by_space[1:])
                            print_to_all = await self.server.run_command(self, cmd_by_space[0], args)
                            if print_to_all:
                                await self.server.send_to_all(msg, self)
                    else:
                        await self.server.send_to_all(msg, self)
                    log_message(self.nick, self.addr, msg)
        except ws.exceptions.ConnectionClosedOK as e:
            await self.close()
        except Exception as e:
            print(e)
            await self.close()
