import os
import sqlite3
import parsable
parsable = parsable.Parsable()
import pomagma.util


STORE = os.path.join(pomagma.util.DATA, 'corpus.db')
SCHEMA = '''(
    id text,
    name text,
    code text,
    args text
)'''


def TODO():
    raise NotImplementedError('TODO')


def table_exists(conn, name):
    cursor = conn.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
        ''',
        (name,),
    )
    return cursor.fetchone() is not None


class Corpus:
    def __init__(self):
        dirname = os.path.dirname(STORE)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        conn = sqlite3.connect(STORE)
        self.conn = conn
        if not table_exists(conn, 'lines'):
            print 'creating lines table'
            conn.execute('CREATE TABLE lines {}'.format(SCHEMA))
            conn.commit()

    def close(self):
        self.conn.close()


@parsable.command
def pull():
    '''
    Pull local corpus from git working tree.
    '''
    TODO()


@parsable.command
def push():
    '''
    Push local corpus to git working tree.
    '''
    TODO()


if __name__ == '__main__':
    parsable.dispatch()
