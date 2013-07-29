/**
 * Unit testing.
 */

define(['log'],
function(log)
{
  var test = function (title, callback) {
    callback = callback || function(){ $.globalEval(title); };
    callback.title = title;
    syncTests.push(callback);
  };

  test.async = function (title, callback, delay) {
    delay = delay || 100;
    assert(delay >= 0, 'bad delay: ' + delay);
    callback.title = title;
    callback.delay = delay;
    asyncTests.push(callback);
  };

  var testing = false;
  var hasRun = false;
  var syncTests = [];
  var asyncTests = [];
  var waitingTests = {};
  var failedTests = [];

  test.testing = function () { return testing; }
  test.hasRun = function () { return hasRun; }
  test.testCount = function () { return syncTests.length + asyncTests.length; }
  test.failCount = function () { return failedTests.length; }

  var startWaiting = function (callback) {
    var title = callback.title;
    assert(!_.has(waitingTests, title), 'duplicate test: ' + title);
    waitingTests[title] = callback;
  };

  var done = function (callback) {
    var title = callback.title;
    assert(_.has(waitingTests, title), 'test succeded twice: ' + title);
    delete waitingTests[title];
    if (_.isEmpty(waitingTests)) {
      hasRun = true;
      doneAll();
    }
  };

  var doneAll = function () {
    doneAll = function(){};

    for (var title in waitingTests) {
      log('Failed ' + title);
      failedTests.push(waitingTests[title]);
    }

    if (_.isEmpty(failedTests)) {
      log('[ Passed all tests :) ]');
      $log.css({'background-color': '#afa', 'border-color': '#afa'});
    } else {
      log('[ Failed ' + test.failCount() + ' tests ]');
      $log.css({'background-color': '#faa', 'border-color': '#faa'});
    }

    log.popListener();

    // call all failed tests to get stack traces
    failedTests.forEach(function(failedTest){
      setTimeout(failedTest, 0);
    });
  };

  test.runAll = function (onExit) {
    delete test.runAll;

    drawLog(onExit);
    log('[ Running ' + test.testCount() + ' unit tests ]');
    testing = true;

    waitingTests = {};
    syncTests.forEach(startWaiting);
    asyncTests.forEach(startWaiting);

    syncTests.forEach(function(callback){
      try {
        callback();
        done(callback);
      }
      catch (err) {
        log('FAILED ' + callback.title + '\n  ' + err);
      }
    });

    log('[ Starting ' + asyncTests.length + ' async tests ]');
    var delay = 0;
    asyncTests.forEach(function(callback){
      delay += callback.delay;
      try {
        callback(function(){
          done(callback);
        });
      }
      catch (err) {
        log('FAILED ' + callback.title + '\n  ' + err);
      }
    });
    setTimeout(function(){ doneAll(); }, delay);
  };

  var $log;
  var drawLog = function (onExit) {

    $log = $('<div>')
      .attr({id:'testLog'})
      .css({
        'position': 'absolute',
        'width': '100%',
        'top': '0%',
        'left': '0%',
        'text-align': 'left',
        'color': 'black',
        'background-color': 'white',
        'border': 'solid 8px white',
        'font-size': '10pt',
        'font-family': '"Courier New",Courier,"Nimbus Mono L",fixed,monospace',
        'z-index': '99'
      })
      .appendTo(document.body);

    log.pushListener(function (message) {
      $('<pre>').text(message).appendTo($log);
    });

    if (onExit !== undefined) {

      $log.css({
            'width': '80%',
            'left': '10%',
            'border-radius': '16px',
            });

      var $shadow = $('<div>')
        .css({
          'position': 'fixed',
          'width': '100%',
          'height': '100%',
          'top': '0%',
          'left': '0%',
          'background-color': 'black',
          'opacity': '0.5',
          'z-index': '98'
        })
        .attr({title:'click to exit test results'})
        .click(function(){
          $log.remove();
          $shadow.remove();
          testing = false;
          onExit();
        })
        .appendTo(document.body);
    }

    return $log;
  };

  return test;
});
