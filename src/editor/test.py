import functools
import time
import multiprocessing
import splinter
import pomagma.editor.app

TEST_COUNT = 23  # this must be updated every time tests are added

PORT = pomagma.editor.app.PORT + 1
server = None
browser = None
failure_count = 0


def count_failures(fun):
    @functools.wraps(fun)
    def decorated():
        global failure_count
        failure_count += 1
        fun()
        failure_count -= 1
    return decorated


def setUp():
    global server
    server = multiprocessing.Process(
        target=pomagma.editor.app.serve,
        kwargs={'port': PORT, 'reloader': False})
    print '---- starting server with pid {} ----'.format(server.pid)
    server.start()

    global browser
    browser = splinter.Browser()
    #browser = splinter.Browser('phantomjs')


def tearDown():
    server.terminate()
    if failure_count == 0:
        browser.quit()


@count_failures
def test_all():

    browser.visit('http://localhost:{}/#test'.format(PORT))
    browser.execute_script(
        '''
        window.pytest = undefined;
        require(["test"], function (test) {
            window.pytest = test;
        });
        ''')
    while not browser.evaluate_script('pytest && pytest.hasRun()'):
        print 'waiting...'
        time.sleep(0.1)
    fail_count = browser.evaluate_script('pytest.failCount()')
    assert fail_count == 0, '{} tests failed'.format(fail_count)
    test_count = browser.evaluate_script('pytest.testCount()')
    assert test_count == TEST_COUNT,\
        'ERROR expected {} tests, actual {}'.format(TEST_COUNT, test_count)
