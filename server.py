import socket as sc
from threading import Thread
from datetime import datetime
from time import sleep
import os
import signal
from typing import Union
import argparse
import sys

from constants import *
from security import *


class Connection(Thread):
    @staticmethod
    def makenew(sock, addr, server, n):
        conn = Connection(sock, addr, server, n)
        conn.start()
        return conn

    def __init__(self, sock, addr, server, n):
        Thread.__init__(self)
        self.sock = sock
        self.addr = addr

        self.server = server

        self.msgs = []

        self.nick = str(n)

        self.send(self.server.pbl_key.export_key())
        self.c_key = import_key(self.recv())
        self.send_encrypted(self.nick)

    def send(self, msg: bytes):
        self.sock.send(bytes(str(len(msg)).zfill(
            MSG_ZFILL), encoding=ENCODING) + msg)

    def send_encrypted(self, msg: str):
        msg_bytes = encrypt(msg, self.c_key)
        self.send(msg_bytes)

    def recv(self):
        n_bytes = int(self.sock.recv(MSG_ZFILL))
        msg_bytes = self.sock.recv(n_bytes)
        return msg_bytes

    def recv_decrypted(self):
        msg_bytes = self.recv()
        return decrypt(msg_bytes, self.server.prv_key)

    def run(self):
        def close():
            self.server.conns.remove(self)
            self.sock.close()

        try:
            while self.server.running:
                msg = self.recv_decrypted()
                print(f'[*][{datetime.now()}]  ' + self.nick + ' > ' + msg)
                _msg = msg.replace('  ', ' ')
                while '  ' in _msg:
                    _msg = _msg.replace('  ', ' ')
                if _msg.split(' ')[0].lower() == '/nick' and len(_msg.split(' ')) > 1:
                    self.nick = _msg.split(' ')[1]
                self.server.send_to_all(msg, self)
                log_message(self, msg)
        except ConnectionResetError:
            print(f'[!][{datetime.now()}] Connection error, closing connection')
            close()
        except TimeoutError:
            print(f'[!][{datetime.now()}] Timeout error, closing connection')
            close()
        except Exception as e:
            print(
                f'[!][{datetime.now()}] Error occured: {e}, closing connection')
            close()


class Server:
    def __init__(self, ip: str, port: int, max_conn: -1):
        self.ip = ip
        self.port = port
        self.addr = (self.ip, self.port)
        self.max_conn = max_conn

        self.running = True
        self.conns = []

        self.prv_key, self.pbl_key = generate_keys()
        self.sock = sc.socket(sc.AF_INET, sc.SOCK_STREAM)
        log_start()
        self.run_server()

    def start_exit_thread(self):
        def quit_thread():
            try:
                while True:
                    cmd = input('').lower()
                    if cmd in ('q', 'quit', ':q', ':q!', 'exit'):
                        os.kill(os.getpid(), signal.SIGINT)
                    elif cmd == 'help':
                        print(
                            f'> enter any of "q", "quit", ":q", ":q!", "exit" and press enter to quit')
                    else:
                        print(f'[!] Command unknown')
            except EOFError:
                os.kill(os.getpid(), signal.SIGINT)
        Thread(target=quit_thread).start()

    def run_server(self):
        try:
            self.sock.bind(self.addr)
            self.sock.listen(self.max_conn)
        except OSError as e:
            print(f'[!][{datetime.now()}] Error binding, you propably are propably trying to run multiple servers on same port at the same time')
            return

        print(f'[*][{datetime.now()}] Server Running')
        print(f'[*][{datetime.now()}] Listening on port {self.port}')

        self.start_exit_thread()

        n = 1

        while self.running:
            (client_sock, addr) = self.sock.accept()
            ct = Connection.makenew(client_sock, addr, self, n)
            self.conns.append(ct)
            print(f'[*][{datetime.now()}] User {addr} ({n}) logged in')
            log_login(addr, str(n))
            self.send_to_all(f'User {n} logged in', str(n))
            n += 1

    def send_to_all(self, msg, author: Union[Connection, str]):
        msg = (author.nick if isinstance(author, Connection)
               else author) + NAME_SPLITTER + msg
        for conn in self.conns:
            # conn = Connection()
            conn.send_encrypted(msg)


def log_message(conn: Connection, msg):
    with open('msgs.log', 'a', encoding='utf-8') as f:
        f.writelines(
            [f'[{datetime.now()}] {conn.nick} {conn.addr}: {msg}', '\n'])


def log_start():
    with open('msgs.log', 'a') as f:
        f.write(f'[{datetime.now()}] Server started\n')


def log_login(addr, nick):
    with open('msgs.log', 'a') as f:
        f.write(f'[{datetime.now()}] User {addr} ({nick}) logged in\n')


def get_ip():
    sock = sc.socket(sc.AF_INET, sc.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    # print("[*] Write this IP to other computers: " + sock.getsockname()[0])
    server = sock.getsockname()[0]
    sock.close()
    sleep(0.5)
    return server


if __name__ == '__main__':
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
    print(f'[*][{datetime.now()}] You are running version {VERSION}')

    _ip = get_ip()

    print(f"[*][{datetime.now()}] Running on {(_ip, _port)}")
    Server(_ip, _port, 5)
