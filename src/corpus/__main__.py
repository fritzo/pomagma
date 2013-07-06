import parsable
parsable = parsable.Parsable()
import pomagma.corpus


@parsable.command
def list_modules(prefix=''):
    '''
    Print list of all modules in corpus.
    '''
    modules = pomagma.corpus.list_modules()
    for module in modules:
        print module


if __name__ == '__main__':
    parsable.dispatch()
