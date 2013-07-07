
var ui = (function(){
var ui = {};

var cursor;

ui.draw = function () {
  var root = ast.getRoot(cursor);
  //var text = root.polish();
  var text = root.lines().join('\n');
  $('#code').html(text);
};

ui.move = function (direction) {
  // log('move: ' + direction);
  if (cursor.tryMove(direction)) {
    ui.draw();
  } else {
    TODO('visual bell');
  }
};

var query_handle_keydown = function (event) {
  console.log(event.which);
  switch (event.which) {
    case 13: // enter
      event.preventDefault();
      $('#query').blur();
      break;
  }
};

var code_handle_keydown = function (event) {
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
      ui.move('U');
      event.preventDefault();
      break;

    case 40: // down
      ui.move('D');
      event.preventDefault();
      break;

    case 37: // left
      ui.move('L');
      event.preventDefault();
      break;

    case 39: // right
      ui.move('R');
      event.preventDefault();
      break;

    case 27: // escape
      event.preventDefault();
      $('#query').focus();
      break;
  }
};

ui.main = function () {

  var start = [
    'DEFINE VARY example',
    'LET VARY test APPLY VARY this VARY test',
    'ABSTRACT QUOTE VARY this APPLY VARY is APPLY VARY a VARY test'
    ].join(' ');
  cursor = ast.parse('CURSOR ' + start);
  ui.draw();

  var $query = $('#query');
  $query.focus(function(){
    console.log('query');
    $(window).off('keydown').on('keydown', query_handle_keydown);
  });
  $query.blur(function(){
    console.log('code');
    $(window).off('keydown').on('keydown', code_handle_keydown);
  });
  $query.focus();
};

return ui;
})(); // ui
