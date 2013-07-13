import os
import mock
import pomagma.util
import pomagma.corpus


STORE = os.path.join(pomagma.util.DATA, 'test', 'corpus.db')


def test_connect():
    corpus = pomagma.corpus.Corpus()
    corpus.close()


def test_create_database():
    if os.path.exists(STORE):
        os.remove(STORE)
    with mock.patch('pomagma.corpus.STORE', new=STORE):
        corpus = pomagma.corpus.Corpus()
        conn = corpus.conn
        assert pomagma.corpus.table_exists(conn, 'lines')
        corpus.close()
