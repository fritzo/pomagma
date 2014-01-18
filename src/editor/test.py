import functools
import time
import splinter
import pomagma.editor.app
import pomagma.analyst.test

TEST_COUNT = 28  # this must be updated every time tests are added

PORT = pomagma.editor.app.PORT + 1
editor = None
analyst = None
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


def setup_module():
    global analyst
    analyst = pomagma.analyst.test.serve()
    print '---- started analyst with pid {} ----'.format(analyst.pid)

    global editor
    editor = pomagma.editor.serve(
        port=PORT,
        address=pomagma.analyst.test.ADDRESS,
        reloader=False)
    print '---- started editor with pid {} ----'.format(editor.pid)

    global browser
    browser = splinter.Browser()
    #browser = splinter.Browser('phantomjs')


def teardown_module():
    editor.terminate()
    analyst.stop()
    if failure_count == 0:
        browser.quit()


@count_failures
def test_all(retries=2):

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
