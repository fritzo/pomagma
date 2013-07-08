var edit = (function(){
var edit = {};

var cursor;

edit.draw = function () {
  var root = ast.getRoot(cursor);
  //var text = root.polish();
  var text = root.lines().join('\n');
  $('#code').html(text);
};

edit.move = function (direction) {
  // log('move: ' + direction);
  if (cursor.tryMove(direction)) {
    edit.draw();
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
      edit.move('U');
      event.preventDefault();
      break;

    case 40: // down
      edit.move('D');
      event.preventDefault();
      break;

    case 37: // left
      edit.move('L');
      event.preventDefault();
      break;

    case 39: // right
      edit.move('R');
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
    'DEFINE VARY example',
    'LET VARY test APPLY VARY this VARY test',
    'ABSTRACT QUOTE VARY this APPLY VARY is APPLY VARY a VARY test'
    ].join(' ');
  cursor = ast.parse('CURSOR ' + start);
  edit.draw();

  var $code = edit.$code = $('#code');
  $code.focus(function(){
    $(window).off('keydown').on('keydown', handle_keydown);
  });
  $code.blur(function(){
    $(window).off('keydown');
  });

});

return edit;
})(); // edit
