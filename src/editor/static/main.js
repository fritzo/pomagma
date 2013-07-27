require(['log', 'test', 'corpus', 'analyst', 'editor', 'controller'],
function( log,   test,   corpus,   analyst,   editor,   controller)
{

  var main = function () {
    editor.load();
    controller.main();
  };

  if (window.location.hash && window.location.hash.substr(1) === 'test') {
    var oldTitle = document.title;
    document.title = 'Test - ' + oldTitle;
    test.runAll(function(){
      document.title = oldTitle;
      window.location.hash = '';
      $(main);
    });
  } else {
    $(main);
  }
});
