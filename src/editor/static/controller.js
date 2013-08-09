define(['log', 'test', 'editor', 'keycode'],
function(log,   test,   editor,   keycode)
{
  var controller = {};

  var setMode = function (name) {
    log('mode = ' + name);
    var mode = modes[name];
    $(window).off('keydown').on('keydown', mode.keydown);
  };

  var suggest = (function () {
    var picklist;
    var pos;

    var render = function () {
      picklist.forEach(function(term, index){
        if (index == pos) {
          log('SUGGEST<>' + term.print);
        } else {
          log('SUGGEST  ' + term.print);
        }
      });
    };

    var suggest = function () {
      picklist = editor.suggest();
      pos = 0;
      render();
    };

    suggest.prev = function () {
      pos = (pos + picklist.length - 1) % picklist.length;
      render();
    };

    suggest.next = function () {
      pos = (pos + 1) % picklist.length;
      render();
    };

    suggest.done = function () {
      picklist = [];
      pos = 0;
      render();
    };

    suggest.pick = function () {
      editor.replace(picklist[pos]);
      done();
    };

    return suggest;
  })();

  var modes = {};

  modes.move = {
    keydown: function (event) {
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

        case keycode.space:
        case keycode.enter:
          suggest();
          setMode('edit');
          break;

        default:
          return;
      }
      event.preventDefault();
    }
  };

  modes.edit = {
    keydown: function (event) {
      console.log(event.which);
      switch (event.which) {
        case keycode.backspace:
        case keycode['delete']:
          suggest.done();
          editor.remove();
          setMode('move');
          break;

        case keycode.up:
          suggest.prev();
          break;

        case keycode.down:
          suggest.next();
          break;

        case keycode.enter:
        case keycode.space:
          suggest.pick();
          setMode('move');
          break;

        case keycode['escape']:
          suggest.done();
          setMode('move');
          break;

        default:
          return;
      }
      event.preventDefault();
    }
  };

  controller.main = function () {
    setMode('move');
  };

  return controller;
});
