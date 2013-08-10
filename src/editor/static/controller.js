define(['log', 'test', 'editor', 'keycode'],
function(log,   test,   editor,   keycode)
{
  var suggest = function () {
    var $suggest = $('#suggest');
    var picklist = editor.suggest();

    $suggest.empty();
    picklist.forEach(function(term){
      $suggest.append($('<pre>').html(term.render));
    });

    var suggest = function () {
      render();
    };

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
          break;
        } else {
          editor.moveLine(-1);
          break;
        }

      case keycode.down:
        if (event.shiftKey) {
          editor.move('D');
          break;
        } else {
          editor.moveLine(+1);
          break;
        }

      case keycode.left:
        if (event.shiftKey) {
          editor.move('U');
          break;
        } else {
          editor.move('L');
          break;
        }

      case keycode.right:
        if (event.shiftKey) {
          editor.move('U');
          break;
        } else {
          editor.move('R');
          break;
        }

      case keycode.backspace:
      case keycode['delete']:
        editor.remove();
        break;

      case keycode.a:
        if (event.shiftKey) {
          editor.insertAssert();
          break;
        }

      case keycode.d:
        if (event.shiftKey) {
          editor.insertDefine();
          break;
        }

      // TODO
      // l for let
      // \ for lambda
      // ! or T for TOP
      // _ or B for BOT
      // { for QUOTE
      // space for APP
      // | for JOIN
      // [a-z] for variable

      case keycode.enter:
        // TODO commit; simplify
        break;

      default:
        return;
    }
    suggest();
    event.preventDefault();
  };

  var main = function () {
    $(window).off('keydown').on('keydown', handleKeydown);
  };

  return {
    main: main
  };
});
