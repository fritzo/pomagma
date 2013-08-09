define(['log', 'test', 'editor', 'keycode'],
function(log,   test,   editor,   keycode)
{
  var controller = {};

  var setMode = function (handler) {
    $(window).off('keydown').on('keydown', handler);
  };

  var handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // dispatch further on:
      //   event.shiftKey
      //   event.ctrlKey
      //   event.altKey
      //   event.metaKey

      case keycode.up:
        if (event.shiftKey) {
          editor.move('U');
        } else {
          editor.moveLine(-1);
        }
        break;

      case keycode.down:
        if (event.shiftKey) {
          editor.move('D');
        } else {
          editor.moveLine(+1);
        }
        break;

      case keycode.left:
        if (event.shiftKey) {
          editor.move('U');
        } else {
          editor.move('L');
        }
        break;

      case keycode.right:
        if (event.shiftKey) {
          editor.move('U');
        } else {
          editor.move('R');
        }
        break;

      case keycode.enter:
        editor.suggest();
        break;

      default:
        return;
    }
    event.preventDefault();
  };

  var insertHandler = function (event) {
  };

  controller.main = function () {
    setMode(handleKeydown);
  };

  return controller;
});
