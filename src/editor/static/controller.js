define(['log', 'test', 'editor'],
function(log,   test,   editor)
{
  var controller = {};

  var handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // see http://www.javascripter.net/faq/keycodes.htm

      case 13: // enter
        // TODO
        event.preventDefault();
        break;

      case 27: // escape
        // TODO
        event.preventDefault();
        break;

      case 32: // space
        // TODO
        event.preventDefault();
        break;

      case 9: // tab
        editor.moveCursor(+1);
        event.preventDefault();
        break;

      case 38: // up
        if (event.shiftKey) {
          editor.moveCursor(+1);
        } else {
          editor.move('U');
        }
        event.preventDefault();
        break;

      case 40: // down
        if (event.shiftKey) {
          editor.moveCursor(-1);
        } else {
          editor.move('D');
        }
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
    }
  };

  controller.main = function () {
    $(window).on('keydown', handleKeydown);
  };

  return controller;
});
