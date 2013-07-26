define(['log', 'test', 'compiler', 'ast', 'corpus'],
function(log,   test,   compiler,   ast,   corpus)
{
  var editor = {};

  var cursorPos = 0;
  var ids = [];
  var asts = {};  // id -> ast
  var $lines = {};  // id -> dom node
  var cursor = null;

  var sortLines = function (lineSet) {
    /*
    Return a heuristically sorted list of definitions.

    TODO use approximately topologically-sorted order.
    (R1) "A Technique for Drawing Directed Graphs" -Gansner et al
      http://www.graphviz.org/Documentation/TSE93.pdf
    (R2) "Combinatorial Algorithms for Feedback Problems in Directed Graphs"
      -Demetrescu and Finocchi
      http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1.9435
    */
    lineArray = [];
    for (var id in lineSet) {
      lineArray.push(lineSet[id]);
    }
    return lineArray;
  };

  editor.move = function (direction) {
    // log('move: ' + direction);
    if (cursor.tryMove(direction)) {
      editor.draw();
    } else {
      TODO('visual bell');
    }
  };

  var renderLine = function (id) {
    var root = ast.getRoot(asts[id]);
    var lambda = ast.dump(root);
    var html = compiler.render(lambda);
    $lines[id].html(html);
  };

  var removeCursor = function () {
    if (cursor !== null) {
      log('removing cursor');
      ast.cursor.remove(cursor);
      var id = ids[cursorPos];
      renderLine(id);
      cursor = null;
    }
  };

  var moveCursor = function (delta) {
    removeCursor();
    cursorPos = (cursorPos + ids.length + delta) % ids.length;
    var id = ids[cursorPos];
    log('moving cursor to id ' + id);
    cursor = ast.cursor.create();
    ast.cursor.insertAbove(cursor, asts[id]);
    renderLine(id);
  };

  editor.load = function () {

    ids = [];
    asts = [];
    corpus.findAllLines().forEach(function(id){
      ids.push(id);
      var line = corpus.findLine(id);
      var code = compiler.parseLine(line);
      var tree = compiler.fromCode(code);
      var lambda = compiler.toLambda(tree);
      asts[id] = ast.load(lambda);
    });
    assert(ids.length > 0, 'corpus is empty');

    var div = $('#code')[0];
    $lines = {};
    corpus.findAllLines().forEach(function(id){
      $lines[id] = $('<pre>').attr('id', 'line' + id).appendTo(div);
      renderLine(id);
    });

    cursorPos = 0;
    moveCursor(0);
  };

  handleKeydown = editor.handleKeyDown = function (event) {
    console.log(event.which);
    switch (event.which) {
      // see http://www.javascripter.net/faq/keycodes.htm

      case 9: // tab
        $('#query').focus();
        event.preventDefault();
        break;

      case 32: // space
        event.preventDefault();
        break;

      case 38: // up
        moveCursor(+1);
        //editor.move('U');
        event.preventDefault();
        break;

      case 40: // down
        moveCursor(-1);
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
        $('#query').focus();
        event.preventDefault();
        break;
    }
  };

  editor.focus = function () {
    log('editor.focus');
    $('#cursor').attr('class', 'cursor');
    $(window).off('keydown').on('keydown', handleKeydown);
  };

  editor.blur = function () {
    $('#cursor').attr('class', null);
  };

  return editor;
});
