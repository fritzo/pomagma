import functools
import time
import splinter

TEST_COUNT = 20  # this must be updated every time tests are added

failure_count = 0
browser = None


def count_failures(fun):
    @functools.wraps(fun)
    def decorated():
        global failure_count
        failure_count += 1
        fun()
        failure_count -= 1
    return decorated


def setUp():
    global browser
    browser = splinter.Browser()
    #browser = splinter.Browser('phantomjs')


def tearDown():
    if failure_count == 0:
        browser.quit()


@count_failures
def test_all():
    browser.visit('http://localhost:34934/#test')
    browser.execute_script('window.test = require("test");')
    while not browser.evaluate_script('test.hasRun()'):
        print 'waiting...'
        time.sleep(0.1)
    fail_count = browser.evaluate_script('test.failCount()')
    assert fail_count == 0, '{} tests failed'.format(fail_count)
    test_count = browser.evaluate_script('test.testCount()')
    assert test_count == TEST_COUNT,\
        'ERROR expected {} tests, actual {}'.format(TEST_COUNT, test_count)
