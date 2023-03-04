from __future__ import annotations
from threading import Thread
import websockets as ws
import asyncio
from json import loads as jloads, dumps as jdumps

from log import log_message, log_disconnect, log_connect
from security import Symmetric, Asymmetric

from typing import TYPE_CHECKING, Any, AsyncIterator, TypedDict, Literal

if TYPE_CHECKING:
    from server import Server


class ToServerMessage(TypedDict):
    type: Literal["message"] | Literal["command"]
    content: str | None
    command: str | None


class FromServerMessage(TypedDict):
    type: Literal["message"] | Literal["command"]
    content: str | None
    command: str | None
    command_args: str | None
    author: str
    author_id: int
    recipient: str
    recipient_id: int


class Connection:
    def __init__(
        self, ws: ws.WebSocketServerProtocol, addr: str, server: Server, nick: str
    ):
        self.ws = ws
        self.addr = addr

        self.server = server

        self.nick = nick
        self.id = id(self)
        self.sym = Symmetric()

    async def send_plain(self, msg: bytes):
        await self.ws.send(msg)

    async def recv_plain(self) -> bytes:
        return await self.ws.recv()

    async def _recv_asym(self) -> str:
        return self.server.local_asym.decrypt(await self.recv_plain())

    async def _send_asym(self, msg: str):
        return await self.send_plain(self.remote_asym.encrypt(msg))

    async def _send_bytes_asym(self, msg: bytes):
        return await self.send_plain(self.remote_asym.encrypt_bytes(msg))

    async def _recv_sym(self) -> str:
        return self.sym.decrypt(await self.recv_plain())

    async def _send_sym(self, msg: str):
        enc = self.sym.encrypt(msg)
        return await self.send_plain(enc)

    async def send_message(self, msg_content: str, author: Connection):
        msg: FromServerMessage = {
            "type": "message",
            "content": msg_content,
            "author": author.nick,
            "author_id": author.id,
            "recipient": self.nick,
            "recipient_id": self.id,
        }

        msg_str: str = jdumps(msg)
        self._send_sym(msg_str)

    async def send_executed_command(self, cmd: str, cmd_args: str, author: Connection):
        msg: FromServerMessage = {
            "type": "command",
            "command": cmd,
            "command_args": cmd_args,
            "author": author.nick,
            "author_id": author.id,
            "recipient": self.nick,
            "recipient_id": self.id,
        }

        msg_str: str = jdumps(msg)
        self._send_sym(msg_str)

    async def resend_message(self, msg: FromServerMessage, author: Connection):
        msg.update(
            {
                "author": author.nick,
                "author_id": author.id,
                "recipient": self.nick,
                "recipient_id": self.id,
            }
        )

        msg_str: str = jdumps(msg)
        await self._send_sym(msg_str)

    async def recv_data(self) -> ToServerMessage:
        data = await self._recv_sym()
        return jloads(data)

    async def close(self, error: str = None):
        await self.ws.close()
        await self.server.send_close(self)
        if error:
            log_disconnect(self.addr, self.nick, reason=f"Error: {error}")
        else:
            log_disconnect(self.addr, self.nick)

    async def __aiter__(self) -> AsyncIterator[ToServerMessage]:
        try:
            while True:
                yield await self.recv_data()
        except ws.ConnectionClosedOK:
            return

    async def run(self):
        try:
            key = self.server.local_asym.export_public()
            await self.send_plain(key)
            self.remote_asym = Asymmetric.import_from(await self.recv_plain())
            await self._send_bytes_asym(self.sym.key)
            log_connect(self.addr, self.nick)

            async for msg in self:
                if msg["type"] == "message":
                    await self.server.send_msg_to_all(msg, self)
                    log_message(self.nick, self.addr, msg["content"])

        except ws.exceptions.ConnectionClosedOK as e:
            await self.close()
        except Exception as e:
            print(e)
            await self.close()
