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

  var renderLine = function (id) {
    if (id === undefined) {
      id = ids[cursorPos];
    }
    var root = ast.getRoot(asts[id]);
    var lambda = ast.dump(root);
    var html = compiler.render(lambda);
    $lines[id].html(html);
  };

  var removeCursor = function () {
    if (cursor !== null) {
      ast.cursor.remove(cursor);
      var id = ids[cursorPos];
      renderLine(id);
    } else {
      cursor = ast.cursor.create();
    }
  };

  var moveCursor = editor.moveCursor = function (delta) {
    removeCursor();
    cursorPos = (cursorPos + ids.length + delta) % ids.length;
    var id = ids[cursorPos];
    log('moving cursor to id ' + id);
    ast.cursor.insertAbove(cursor, asts[id]);
    renderLine(id);
  };

  editor.move = function (direction) {
    // log('move: ' + direction);
    if (ast.cursor.tryMove(cursor, direction)) {
      renderLine();
    } else {
      //TODO('visual bell');
    }
  };

  editor.load = function () {
    ids = [];
    asts = {};
    corpus.findAllLines().forEach(function(id){
      ids.push(id);
      var line = corpus.findLine(id);
      var lambda = compiler.loadLine(line);
      log('DEBUG ' + lambda);
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

  editor.suggest = function () {
    var nbhd = ast.neighborhood(cursor);
    nbhd.forEach(function(term){
      log('DEBUG suggest ' + compiler.print(term));
    });
  };

  editor.debug = function () {
    return {
      cursorPos: cursorPos,
      ids: ids,
      asts: asts,
      $lines: $lines,
      cursor: cursor
    };
  };

  return editor;
});
