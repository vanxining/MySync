import logging


class MyEvent(object):
    def __init__(self, tag, src_path, data):
        self.tag = tag
        self.src_path = src_path
        self.data = data

    def __str__(self):
        size = 3 + 8 * 3 + len(self.src_path) + len(self.data)

        s = ""
        s += "%08d" % size
        s += self.tag
        s += "%08d" % len(self.src_path)
        s += self.src_path
        s += "%08d" % len(self.data)
        s += self.data

        return s

    def __repr__(self):
        s = "{} {} ({} bytes)".format(self.tag, self.src_path, len(self.data))

        return s


def decode_event(s):
    try:
        tag = s[:3]
        s = s[3:]

        size = int(s[:8])
        s = s[8:]
        src_path = s[:size]
        s = s[size:]

        size = int(s[:8])
        s = s[8:]

        return MyEvent(tag, src_path, s)
    except Exception as e:
        logging.error(e)

        return MyEvent("", "", "")
