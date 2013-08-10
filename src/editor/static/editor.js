define(['log', 'test', 'compiler', 'ast', 'corpus'],
function(log,   test,   compiler,   ast,   corpus)
{
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

  var moveLine = function (delta) {
    removeCursor();
    cursorPos = (cursorPos + ids.length + delta) % ids.length;
    var id = ids[cursorPos];
    log('moving cursor to id ' + id);
    ast.cursor.insertAbove(cursor, asts[id]);
    renderLine(id);
  };

  var move = function (direction) {
    // log('move: ' + direction);
    if (ast.cursor.tryMove(cursor, direction)) {
      renderLine();
    } else {
      //TODO('visual bell');
    }
  };

  var load = function () {
    ids = [];
    asts = {};
    corpus.findAllLines().forEach(function(id){
      ids.push(id);
      var line = corpus.findLine(id);
      var lambda = compiler.loadLine(line);
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
    moveLine(0);
  };

  var remove = function () {
    if (cursor.above == null) {
      TODO('remove line from corpus');
    } else {
      TODO('replace old term with hole');
    }
  };

  var insertAssert = function () {
    TODO('insert assertion below line;');
    TODO('moveLine to assertion');
    TODO('move to assertion HOLE');
  };

  var insertDefine = function () {
    TODO('insert definition below line;');
    TODO('moveLine to assertion');
    TODO('move to assertion HOLE');
  };

  var replace = function (newTerm) {
    TODO('replace old term with new');
  };

  //--------------------------------------------------------------------------
  // Transformations

  var getNeighborhood = (function(){
    // TODO extract these automatically from binder annotations
    var HOLE = compiler.symbols.HOLE;
    var TOP = compiler.symbols.TOP;
    var BOT = compiler.symbols.BOT;
    var VAR = compiler.symbols.VAR;
    var LAMBDA = compiler.symbols.LAMBDA;
    var LETREC = compiler.symbols.LETREC;
    var APP = compiler.symbols.APP;
    var JOIN = compiler.symbols.JOIN;
    var RAND = compiler.symbols.RAND;
    var QUOTE = compiler.symbols.QUOTE;

    return function (cursor) {
      var term = cursor.below[0];
      var result = [];
      var name = term.name;
      var varName = ast.getFresh(term);
      var fresh = VAR(varName);
      if (name === 'ASSERT' || name === 'DEFINE') {
        /* no neighborhood */
      } else if (name === 'HOLE') {
        result.push(
          TOP,
          BOT,
          LAMBDA(fresh, HOLE),
          LETREC(fresh, HOLE, HOLE),
          APP(HOLE, HOLE),
          JOIN(HOLE, HOLE),
          QUOTE(HOLE)
        );
        var locals = ast.getBoundAbove(term);
        locals.forEach(function(varName){
          result.push(VAR(varName));
        });
        var globals = corpus.findAllNames();
        globals.forEach(function(varName){
          result.push(VAR(varName));
        });
      } else {
        // the move to HOLE is achieved elsewhere via DELETE/BACKSPACE
        var dumped = ast.dump(term);
        result.push(
          LAMBDA(fresh, dumped),
          LETREC(fresh, dumped, HOLE),
          LETREC(fresh, HOLE, dumped),
          APP(dumped, HOLE),
          APP(HOLE, dumped),
          JOIN(dumped, HOLE),
          QUOTE(dumped)
        );
      }
      return result;
    };
  })();

  var suggest = function () {
    var terms = getNeighborhood(cursor);
    return _.map(terms, function (term) {
      return {
        ast: term,
        render: compiler.render(term, null)
      };
    });
  };

  //--------------------------------------------------------------------------
  // Interface

  var debug = function () {
    return {
      cursorPos: cursorPos,
      ids: ids,
      asts: asts,
      $lines: $lines,
      cursor: cursor
    };
  };

  return {
    load: load,
    moveLine: moveLine,
    move: move,
    suggest: suggest,
    remove: remove,
    replace: replace,
    insertAssert: insertAssert,
    insertDefine: insertDefine,
    debug: debug,
  };
});
