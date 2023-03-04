from constants import *
from log import *
import sys
from server import get_ip, Server
from termcolor import colored


def run():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        f"--port", type=int, help=f"port number for server", default=PORT
    )
    parser.add_argument(
        f"--version", action="store_true", help="print version and exit"
    )
    args = parser.parse_args()
    if args.version:
        print(f"Version: {VERSION}")
        sys.exit()
    if args.port is not None:
        _port = args.port
    else:
        _port = PORT
    log(f"You are running version {VERSION}")

    _ip = get_ip()

    log(f"Running on {_ip}:{_port}")
    log(
        f"Enter address: {colored(_ip, 'red')} and port: {colored(_port, 'red')} in client to connect"
    )
    Server(_ip, _port)


if __name__ == "__main__":
    run()
