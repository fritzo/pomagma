require(['test', 'corpus', 'editor', 'analyst', 'ui'],
function( test,   corpus,   editor,   analyst,   ui)
{

  var main = function () {
    editor.drawAllLines();
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
