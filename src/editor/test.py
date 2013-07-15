import functools
import time
import splinter

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
    global browser
    browser = splinter.Browser()
    #browser = splinter.Browser('phantomjs')


def tearDown():
    if failure_count == 0:
        browser.quit()


@count_failures
def test_all():
    browser.visit('http://localhost:34934/test')
    while not browser.evaluate_script('test.hasRun()'):
        time.sleep(0.2)
    assert browser.evaluate_script('test.passed()')
