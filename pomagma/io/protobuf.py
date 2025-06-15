import gzip

from pomagma.io import creat


class InFile:
    def __init__(self, filename):
        self._gzip = gzip.GzipFile(filename, "rb")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._gzip.close()

    def read(self, message):
        message.ParseFromString(self._gzip.read())


class OutFile:
    def __init__(self, filename):
        self._file = creat(filename, 0o444)
        self._gzip = gzip.GzipFile(mode="wb", fileobj=self._file)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._gzip.close()
        self._file.close()

    def write(self, message):
        self._gzip.write(message.SerializeToString())
