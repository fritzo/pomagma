require(['log', 'test', 'corpus', 'analyst', 'editor', 'query'],
function( log,   test,   corpus,   analyst,   editor,   query)
{

  var main = function () {
    editor.load();
    $('#query').focus();
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
