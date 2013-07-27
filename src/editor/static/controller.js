define(['log', 'test', 'editor', 'keycode'],
function(log,   test,   editor,   keycode)
{
  var controller = {};

  var handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // dispatch furher on:
      //   event.shiftKey
      //   event.ctrlKey
      //   event.altKey
      //   event.metaKey

      case keycode.enter:
        // TODO
        event.preventDefault();
        break;

      case keycode.escape:
        // TODO
        event.preventDefault();
        break;

      case keycode.space:
        // TODO
        event.preventDefault();
        break;

      case keycode.tab:
        editor.moveCursor(+1);
        event.preventDefault();
        break;

      case keycode.up:
        if (event.shiftKey) {
          editor.moveCursor(-1);
        } else {
          editor.move('U');
        }
        event.preventDefault();
        break;

      case keycode.down:
        if (event.shiftKey) {
          editor.moveCursor(+1);
        } else {
          editor.move('D');
        }
        event.preventDefault();
        break;

      case keycode.left:
        editor.move('L');
        event.preventDefault();
        break;

      case keycode.right:
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
