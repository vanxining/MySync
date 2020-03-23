#!/usr/bin/env python3

import argparse
import logging
import os
import time
import traceback
import urllib.request

import watchdog.events
import watchdog.observers

import config
import event as E


Q = E.Queue()


def should_sync(fpath):
    for ignored in config.ignored_path_patterns:
        if ignored in fpath:
            return False

    return os.path.splitext(fpath.lower())[1] in config.file_types


def send_event(url, event):
    data_json = E.jencode(event).encode("utf8")
    try:
        req = urllib.request.Request(url, data=data_json, headers={"Content-Type": "application/json"})
        response_stream = urllib.request.urlopen(req)
        logging.debug(response_stream.read().decode("utf8"))

        return True
    except:
        traceback.print_exc()
        return False


class FileChangedEventHandler(watchdog.events.FileSystemEventHandler):
    def on_deleted(self, event):
        if isinstance(event, watchdog.events.FileDeletedEvent):
            logging.info(event)

            if should_sync(event.src_path):
                Q.push_event(E.FileChangedEvent("DEL", event.src_path, ""))

    def on_created(self, event):
        if isinstance(event, watchdog.events.FileCreatedEvent):
            logging.info(event)

            if should_sync(event.src_path):
                with open(event.src_path, "rb") as inf:
                    Q.push_event(E.FileChangedEvent("NEW", event.src_path,
                        inf.read().decode(config.input_file_encoding)))

    def on_modified(self, event):
        if isinstance(event, watchdog.events.FileModifiedEvent):
            logging.info(event)

            if should_sync(event.src_path):
                with open(event.src_path, "rb") as inf:
                    Q.push_event(E.FileChangedEvent("MOD", event.src_path,
                        inf.read().decode(config.input_file_encoding)))

    def on_moved(self, event):
        if isinstance(event, watchdog.events.FileMovedEvent):
            logging.info(event)

            if should_sync(event.src_path):
                Q.push_event(E.FileChangedEvent("MOV", event.src_path, event.dest_path))


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser(prog="MySync", usage="Sync files between local workstation and remote server")
    parser.add_argument("--path", "-p", type=str, default=".", nargs="?", help="the path to the directory to watch")
    parser.add_argument("--server", "-s", type=str, default="elk", nargs="?", help="the remote server")
    parser.add_argument("--port", "-P", type=int, default=58667, nargs="?", help="the remote port")
    args = parser.parse_args()

    url = "http://{}:{}/".format(args.server, args.port)

    event_handler = FileChangedEventHandler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, args.path, recursive=True)
    observer.start()

    print("Server URL:", url)

    try:
        while True:
            time.sleep(0.2)

            while True:
                event = Q.pop_event()
                if event is None:
                    break

                if not send_event(url, event):
                    Q.put_back_event(event)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
