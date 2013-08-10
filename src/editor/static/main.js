require(['log', 'test', 'corpus', 'analyst', 'editor', 'controller'],
function( log,   test,   corpus,   analyst,   editor,   controller)
{
  var ready = function (cb) {
    $(function(){
      corpus.ready(cb);
    });
  };

  var main = function () {
    editor.load();
    controller.main();
  };

  var testMain = function () {
    var oldTitle = document.title;
    document.title = 'Test - ' + oldTitle;
    test.runAll(function(){
      document.title = oldTitle;
      window.location.hash = '';
      main();
    });
  };

  if (window.location.hash && window.location.hash.substr(1) === 'test') {
    ready(testMain);
  } else {
    ready(main);
  }
});
