import gzip


class InFile(object):
    def __init__(self, filename):
        self._file = gzip.GzipFile(filename, 'rb')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._file.close()

    def read(self, message):
        message.ParseFromString(self._file.read())


class OutFile(object):
    def __init__(self, filename):
        self._file = gzip.GzipFile(filename, 'wb')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._file.close()

    def write(self, message):
        self._file.write(message.SerializeToString())
