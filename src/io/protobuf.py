import gzip
import os


class InFile(object):
    def __init__(self, filename):
        self._gzip = gzip.GzipFile(filename, 'rb')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._gzip.close()

    def read(self, message):
        message.ParseFromString(self._gzip.read())


class OutFile(object):
    def __init__(self, filename):
        # this may be insufficient to set permissions
        # see http://stackoverflow.com/a/15015748/1224437
        fid = os.open(filename, os.O_WRONLY | os.O_CREAT, 0444)
        self._file = os.fdopen(fid, 'wb')
        self._gzip = gzip.GzipFile(mode='wb', fileobj=self._file)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._gzip.close()
        self._file.close()

    def write(self, message):
        self._gzip.write(message.SerializeToString())