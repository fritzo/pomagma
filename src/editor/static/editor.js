define(['log', 'test', 'compiler', 'ast', 'corpus', 'navigate'],
function(log,   test,   compiler,   ast,   corpus,   navigate)
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

  var replace = function (newTerm, subs) {
    if (subs !== undefined) {
      newTerm = compiler.substitute('&mdash;', subs, newTerm);
    }
    log('DEBUG ' + compiler.print(newTerm));
    TODO('replace old term with new');
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

  var removeAssert = function () {
    TODO('remove assertion on current line');
    TODO('move to next line');
  };

  var removeDefine = function () {
    TODO('remove definition on current line');
    TODO('move to next line');
  };

  //--------------------------------------------------------------------------
  // Navigation

  var takeBearings = (function(){

    var HOLE = compiler.symbols.HOLE;
    var TOP = compiler.symbols.TOP;
    var BOT = compiler.symbols.BOT;
    var VAR = compiler.symbols.VAR;
    var LAMBDA = compiler.symbols.LAMBDA;
    var LETREC = compiler.symbols.LETREC;
    var APP = compiler.symbols.APP;
    var JOIN = compiler.symbols.JOIN;
    var QUOTE = compiler.symbols.QUOTE;
    var ASSERT = compiler.symbols.ASSERT;
    var DEFINE = compiler.symbols.DEFINE;
    var DASH = VAR('&mdash;');

    var render = function (term) {
      return $('<pre>').html(compiler.render(term));
    };

    var action = function (cb) {
      var args = Array.prototype.slice.call(arguments, 1);
      return function () {
        cb.apply(null, args);
        takeBearings();
      };
    };

    var toggleHelp = function () {
      $('#navigate').toggle();
    };

    var generic = [
      ['escape', toggleHelp, 'toggle help'],
      ['up', action(moveLine, -1), 'move up'],
      ['down', action(moveLine, 1), 'move down'],
      ['left', action(move, 'L'), 'move left'],
      ['right', action(move, 'R'), 'move right'],
      ['shift+left', action(move, 'U'), 'select'],
      ['shift+right', action(move, 'U'), 'select'],
      ['A', action(insertAssert), render(ASSERT(HOLE))],
      ['D', action(insertDefine), render(DEFINE(VAR('...'), HOLE))]
    ];

    var off = function () {
      navigate.off();
      for (var i = 0; i < generic.length; ++i) {
        navigate.on.apply(null, generic[i]);
      }
    };

    var on = function (name, term, subs) {
      var callback = function () {
        replace(term, subs);
        takeBearings();
      };
      var description = render(term);
      navigate.on(name, callback, description);
    };

    return function () {
      var term = cursor.below[0];
      var name = term.name;
      var varName = ast.getFresh(term);
      var fresh = VAR(varName);

      off();
      if (name === 'ASSERT') {
        navigate.on('backspace', removeAssert, 'delete line');
      } else if (name === 'DEFINE') {
        navigate.on('backspace', removeDefine, 'delete line');
      } else if (name === 'HOLE') {
        on('T', TOP);
        on('_', BOT);
        on('\\', LAMBDA(fresh, HOLE));
        on('L', LETREC(fresh, HOLE, HOLE));
        on('(', APP(HOLE, HOLE));
        on('|', JOIN(HOLE, HOLE));
        on('{', QUOTE(HOLE));

        // TODO select local variable
        //on('v', VAR( ...chooser... ));

        var locals = ast.getBoundAbove(term);
        locals.forEach(function(varName){
          on(varName, VAR(varName));
          // TODO deal with >26 variables
        });
        // TODO select global variable
        //var globals = corpus.findAllNames();
        //globals.forEach(function(varName){
        //  on('g', VAR(varName));
        //});
      } else {
        var dumped = ast.dump(term);
        on('backspace', HOLE);
        on('\\', LAMBDA(fresh, DASH), dumped);
        on('L', LETREC(fresh, DASH, HOLE), dumped);
        on('.', LETREC(fresh, HOLE, DASH), dumped);
        on('space', APP(DASH, HOLE), dumped);
        on('(', APP(HOLE, DASH), dumped);
        on('|', JOIN(DASH, HOLE), dumped);
        on('{', QUOTE(DASH), dumped);
      }
    };
  })();

  //--------------------------------------------------------------------------
  // Interface

  var main = function () {
    load();
    takeBearings();
    $(window).off('keydown').on('keydown', navigate.trigger);
  };

  return {
    main: main,
    //moveLine: moveLine,
    //move: move,
    //remove: remove,
    //replace: replace,
    //insertAssert: insertAssert,
    //insertDefine: insertDefine,
  };
});
