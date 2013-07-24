define(['log', 'test', 'compiler', 'ast', 'corpus'],
function(log,   test,   compiler,   ast,   corpus)
{
  var editor = {};

  var cursor;

  var $code;
  var $query;
  var $go;

  editor.move = function (direction) {
    // log('move: ' + direction);
    if (cursor.tryMove(direction)) {
      editor.draw();
    } else {
      TODO('visual bell');
    }
  };

  handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // see http://www.javascripter.net/faq/keycodes.htm

      case 9: // tab
        event.preventDefault();
        break;

      case 32: // space
        event.preventDefault();
        break;

      case 38: // up
        editor.move('U');
        event.preventDefault();
        break;

      case 40: // down
        editor.move('D');
        event.preventDefault();
        break;

      case 37: // left
        editor.move('L');
        event.preventDefault();
        break;

      case 39: // right
        editor.move('R');
        event.preventDefault();
        break;

      case 27: // escape
        event.preventDefault();
        $('#query').focus();
        break;
    }
  };

  //$code.focus(function(){
  //  $(window).off('keydown').on('keydown', handleKeydown);
  //});
  //$code.blur(function(){
  //  $(window).off('keydown');
  //});

  editor.drawAllLines = function () {
    var div = $('#code')[0];
    corpus.findAllLines().forEach(function(id){
      var line = corpus.findLine(id);
      var code = compiler.parseLine(line);
      log('DEBUG code = ' + code);
      var tree = compiler.fromCode(code);
      log('DEBUG tree = ' + tree);
      var lambda = compiler.toLambda(tree);
      var html = compiler.render(lambda);

      // TODO load terms from ast
      //var cursor = ast.load(tree);
      //var root = ast.getRoot(cursor);
      //var html = ast.lines(root).join('\n');

      $('<pre>').html(html).attr('id', id).appendTo(div);
    });
  };

  $(function(){
    editor.$code = $('#code');
    editor.$query = $('#query');
  });

  return editor;
});
