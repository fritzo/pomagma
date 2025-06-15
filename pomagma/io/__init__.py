import os


def create_directories(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            if not os.path.exists(path):
                raise e


def creat(filename, mode):
    assert isinstance(mode, int), mode
    # this may be insufficient to set permissions
    # see http://stackoverflow.com/a/15015748/1224437
    fid = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, mode)
    return os.fdopen(fid, "wb")
