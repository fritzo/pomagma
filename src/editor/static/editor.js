define(['log', 'test', 'compiler', 'ast'],
function(log,   test,   compiler,   ast)
{
  var editor = {};

  var cursor;

  editor.draw = function () {
    var root = ast.getRoot(cursor);
    var text = root.lines().join('\n');
    $('#code').html(text);
  };

  editor.move = function (direction) {
    // log('move: ' + direction);
    if (cursor.tryMove(direction)) {
      editor.draw();
    } else {
      TODO('visual bell');
    }
  };

  handle_keydown = function (event) {
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

  $(function(){

    var start = [
      'DEFINE VAR example',
      'LET VAR test APP VAR this VAR test',
      'LAMBDA QUOTE VAR this APP VAR is APP VAR a VAR test'
      ].join(' ');
    var tree = compiler.parse('CURSOR ' + start);
    cursor = ast.load(tree);
    editor.draw();

    var $code = editor.$code = $('#code');
    $code.focus(function(){
      $(window).off('keydown').on('keydown', handle_keydown);
    });
    $code.blur(function(){
      $(window).off('keydown');
    });

  });

  return editor;
});
