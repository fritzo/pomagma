import tables
import parsable


parsable_commands = []
def parsable_command(fun):
    parsable_commands.append(fun)
    return fun


def parsable_dispatch():
    for fun in parsable_commands:
        parsable.command(fun)
    parsable.dispatch()


@parsable_command
def hdf5_ls(filename):
    '''
    Prints directory of hdf5 file
    '''
    f = tables.openFile(filename)
    for o in f:
        print o


if __name__ == '__main__':
    parsable_dispatch()
