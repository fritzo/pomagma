from pomagma.atlas import print_info
import parsable


@parsable.command
def info(filename):
    '''
    Print info about a structure file.
    '''
    print_info(filename)


parsable.dispatch()
