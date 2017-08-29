import json
import thread

from collections import deque


class FileChangedEvent(object):
    def __init__(self, tag, src_path, data):
        self.tag = tag
        self.src_path = src_path
        self.data = data

    def __repr__(self):
        return "{} {} ({} bytes)".format(self.tag, self.src_path, len(self.data))


def as_file_changed_event(dct):
    return FileChangedEvent(dct[u"tag"], dct[u"sourcePath"], dct[u"data"])


def jdecode(raw):
    return json.loads(raw, object_hook=as_file_changed_event)


def jencode(event):
    return json.dumps({
        "tag": event.tag,
        "sourcePath": event.src_path,
        "data": event.data,
    })


class Queue(object):
    def __init__(self):
        self.lock = thread.allocate_lock()
        self.deque = deque()

    def push_event(self, event):
        self.lock.acquire()
        self.deque.append(event)
        self.lock.release()

    def put_back_event(self, event):
        self.lock.acquire()
        self.deque.appendleft(event)
        self.lock.release()

    def pop_event(self):
        self.lock.acquire()
        event = None if len(self.deque) == 0 else self.deque.popleft()
        self.lock.release()

        return event
