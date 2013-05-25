
var ui = (function(){
var ui = {};

var cursor;

ui.draw = function () {
  var root = ast.getRoot(cursor);
  var text = root.polish();
  $(document.body).text(text);
};

ui.move = function (direction) {
  // log('move: ' + direction);
  if (cursor.tryMove(direction)) {
    ui.draw();
  } else {
    TODO('visual bell');
  }
};

$(window).keydown(function (event) {
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
  }
});

ui.main = function () {
  var start = 'ABSTRACT QUOTE VARY this APPLY VARY is APPLY VARY a VARY test';
  cursor = ast.parse('CURSOR ' + start);
  ui.draw();
};

return ui;
})(); // ui
