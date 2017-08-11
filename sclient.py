#!/usr/bin/python

import argparse
import logging
import os
import socket
import time
import traceback

import watchdog.events
import watchdog.observers

import config

from event import MyEvent


g_args = None


def should_sync(fpath):
    return os.path.splitext(fpath.lower())[1] in config.file_types


def connect_to_server():
    s = None

    for res in socket.getaddrinfo(g_args.server, g_args.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res

        try:
            s = socket.socket(af, socktype, proto)
        except socket.error:
            s.close()
            s = None

            traceback.print_exc()
            continue

        try:
            s.connect(sa)
        except socket.error:
            s.close()
            s = None

            traceback.print_exc()
            continue

        break

    if s is None:
        logging.error("Could not connect to server")

    return s


class MyEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self):
        self.socket = None

    def __del__(self):
        self.close_socket()

    def ensure_socket(self):
        retries = 3
        while retries > 0:
            if self.socket is None:
                self.socket = connect_to_server()

            if self.socket is not None:
                break

            retries -= 1

    def close_socket(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def on_deleted(self, event):
        if type(event) is watchdog.events.FileDeletedEvent:
            logging.info(event)

            if should_sync(event.src_path):
                self.send(MyEvent("DEL", event.src_path, ""))

    def on_created(self, event):
        if type(event) is watchdog.events.FileCreatedEvent:
            logging.info(event)

            if should_sync(event.src_path):
                with open(event.src_path, "r") as inf:
                    self.send(MyEvent("NEW", event.src_path, inf.read()))

    def on_modified(self, event):
        if type(event) is watchdog.events.FileModifiedEvent:
            logging.info(event)

            if should_sync(event.src_path):
                with open(event.src_path, "r") as inf:
                    self.send(MyEvent("MOD", event.src_path, inf.read()))

    def on_moved(self, event):
        if type(event) is watchdog.events.FileMovedEvent:
            logging.info(event)

            if should_sync(event.src_path):
                self.send(MyEvent("MOV", event.src_path, event.dest_path))

    def send(self, event):
        retries = 3
        while retries > 0:
            retries -= 1

            if self.socket is None:
                self.ensure_socket()

            if self.socket is None:
                continue

            try:
                self.socket.sendall(str(event))

                break
            except socket.error:
                traceback.print_exc()

                self.close_socket()


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser(prog="MySync", usage="Sync files between local workstation and remote server")
    parser.add_argument("--path", "-p", type=str, default=".", nargs="?", help="the path to the directory to watch")
    parser.add_argument("--server", "-s", type=str, default="dev", nargs="?", help="the remote server")
    parser.add_argument("--port", "-P", type=int, default=58667, nargs="?", help="the remote port")
    global g_args
    g_args = parser.parse_args()

    event_handler = MyEventHandler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, g_args.path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
