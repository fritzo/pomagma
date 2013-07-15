import splinter
import time

browser = None


def setUp():
    global browser
    browser = splinter.Browser()
    #browser = splinter.Browser('phantomjs')


def tearDown():
    browser.quit()


def test_corpus():
    browser.visit('http://localhost:34934/test')
    time.sleep(1)
    while not browser.evaluate_script('test.hasRun()'):
        print 'waiting...'
        time.sleep(1)
    assert browser.evaluate_script('test.passed()')


if __name__ == '__main__':
    setUp()
    try:
        test_corpus()
    finally:
        tearDown()
