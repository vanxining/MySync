#!/usr/bin/python

import argparse
import logging
import os
import shutil
import socket
import sys
import traceback

from event import decode_event


g_args = None


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser(prog="MySync Server", usage="Sync files between local workstation and remote server")
    parser.add_argument("--path", "-p", type=str, default=".", nargs="?", help="the path to the directory to sync")
    parser.add_argument("--port", "-P", type=int, default=58667, nargs="?", help="the remote port")
    global g_args
    g_args = parser.parse_args()

    s = None

    for res in socket.getaddrinfo(None, g_args.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
        af, socktype, proto, canonname, sa = res

        try:
            s = socket.socket(af, socktype, proto)
        except socket.error:
            s = None

            traceback.print_exc()
            continue

        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(sa)
            s.listen(1)
        except socket.error:
            s.close()
            s = None

            traceback.print_exc()
            continue

        break

    if s is None:
        logging.error("Could not open socket")
        sys.exit(1)

    logging.info("Server listening at %d..." % g_args.port)

    while True:
        try:
            conn, addr = s.accept()
            logging.info("Connected by %s:%d" % addr[:2])
        except socket.error:
            traceback.print_exc()
            continue

        try:
            size = conn.recv(8)
            if len(size) < 8:
                continue

            n = int(size)

            raw = conn.recv(n)
            event = decode_event(raw)

            logging.info(repr(event))

            if event.tag in ("NEW", "MOD",):
                with open(event.src_path, "w") as outf:
                    outf.write(event.data)
            elif event.tag == "MOV":
                shutil.move(event.src_path, event.data)
            elif event.tag == "DEL":
                os.remove(event.src_path)
            else:
                logging.error("Unrecognized command: ", raw)
        except:
            traceback.print_exc()
        finally:
            conn.close()


if __name__ == "__main__":
    main()
