define(['log', 'test', 'editor'],
function(log,   test,   editor)
{
  var controller = {};

  var handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // see http://www.javascripter.net/faq/keycodes.htm

      case 9: // tab
        editor.moveCursor(+1);
        event.preventDefault();
        break;

      case 32: // space
        // TODO
        event.preventDefault();
        break;

      case 38: // up
        editor.moveCursor(+1);
        //editor.move('U');
        event.preventDefault();
        break;

      case 40: // down
        editor.moveCursor(-1);
        //editor.move('D');
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
        // TODO
        event.preventDefault();
        break;
    }
  };

  controller.main = function () {
    $(window).off('keydown').on('keydown', handleKeydown);
  };

  return controller;
});
