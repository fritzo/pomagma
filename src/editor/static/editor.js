define(['log', 'test', 'compiler', 'ast', 'corpus', 'navigate'],
function(log,   test,   compiler,   ast,   corpus,   navigate)
{
  var ids = [];
  var asts = {};  // id -> ast
  var $lines = {};  // id -> dom node
  var cursor = null;
  var cursorPos = 0;
  var lineChanged = false;

  //--------------------------------------------------------------------------
  // Corpus Management

  var loadAllLines = function () {
    ids = [];
    asts = {};
    corpus.findAllLines().forEach(function(id){
      ids.push(id);
      var line = corpus.findLine(id);
      var lambda = compiler.loadLine(line);
      asts[id] = ast.load(lambda);
    });
    assert(ids.length > 0, 'corpus is empty');
  };

  var replaceBelow = function (newLambda, subsForDash) {
    if (subsForDash !== undefined) {
      newLambda = compiler.substitute('&mdash;', subsForDash, newLambda);
    }
    //log('replacing with: ' + compiler.print(newLambda));
    var newTerm = ast.load(newLambda);
    cursor = ast.cursor.replaceBelow(cursor, newTerm);
    lineChanged = true;
    renderLine();
  };

  var replaceAbove = function (newLambda, subsForDash) {
    var notRoot = ast.cursor.tryMove('U');
    assert(notRoot, 'cannot replace above root');
    replaceBelow(newLambda, subsForDash);
  };

  var insertAssert = function () {
    TODO('insert assertion below line;');
    TODO('moveCursorLine to assertion');
    TODO('move to assertion HOLE');
  };

  var insertDefine = function () {
    TODO('insert definition below line;');
    TODO('moveCursorLine to assertion');
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

  var commitLine = function () {
    var id = ids[cursorPos];
    var below = cursor.below[0];
    ast.cursor.remove(cursor);
    var root = ast.getRoot(below);
    var lambda = ast.dump(root);
    var line = compiler.dumpLine(lambda);
    line.id = id;
    line = corpus.update(line);
    lambda = compiler.loadLine(line);
    root = ast.load(lambda);
    ast.cursor.insertAbove(cursor, root);
    asts[id] = root;
    renderLine(id);
    lineChanged = false;
  };

  var revertLine = function () {
    var id = ids[cursorPos];
    var line = corpus.findLine(id);
    var lambda = compiler.loadLine(line);
    var root = ast.load(lambda);
    ast.cursor.remove(cursor);
    ast.cursor.insertAbove(cursor, root);
    asts[id] = cursor;
    renderLine(id);
    lineChanged = false;
  };

  //--------------------------------------------------------------------------
  // Rendering

  var renderLine = function (id) {
    if (id === undefined) {
      id = ids[cursorPos];
    }
    var root = ast.getRoot(asts[id]);
    var lambda = ast.dump(root);
    var html = compiler.render(lambda);
    $lines[id].html(html);
  };

  var renderAllLines = function () {
    $lines = {};
    var div = $('#code').empty()[0];
    corpus.findAllLines().forEach(function(id){
      $lines[id] = $('<pre>').attr('id', 'line' + id).appendTo(div);
      renderLine(id);
    });
  };

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

  //--------------------------------------------------------------------------
  // Cursor Movement

  var initCursor = function () {
    cursor = ast.cursor.create();
    cursorPos = 0;
    lineChanged = false;
    var id = ids[cursorPos];
    ast.cursor.insertAbove(cursor, asts[id]);
    renderLine(id);
  };

  var moveCursorLine = function (delta) {
    if (lineChanged) {
      commitLine();
    }
    ast.cursor.remove(cursor);
    renderLine();
    cursorPos = (cursorPos + ids.length + delta) % ids.length;
    var id = ids[cursorPos];
    //log('moving cursor to id ' + id);
    ast.cursor.insertAbove(cursor, asts[id]);
    renderLine(id);
  };

  var moveCursor = function (direction) {
    if (ast.cursor.tryMove(cursor, direction)) {
      renderLine();
    }
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
    var CURSOR = compiler.symbols.CURSOR;
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
      ['?', toggleHelp, 'toggle help'],
      ['enter', action(commitLine), 'commit line'],
      ['escape', action(revertLine), 'revert line'],
      ['up', action(moveCursorLine, -1), 'move up'],
      ['down', action(moveCursorLine, 1), 'move down'],
      ['left', action(moveCursor, 'L'), 'move left'],
      ['right', action(moveCursor, 'R'), 'move right'],
      ['shift+left', action(moveCursor, 'U'), 'select'],
      ['shift+right', action(moveCursor, 'U'), 'select'],
      ['A', action(insertAssert), render(ASSERT(CURSOR(HOLE)))],
      ['D', action(insertDefine), render(DEFINE(CURSOR(VAR('...')), HOLE))]
    ];

    var off = function () {
      navigate.off();
      for (var i = 0; i < generic.length; ++i) {
        navigate.on.apply(null, generic[i]);
      }
    };

    var on = function (name, term, subsForDash) {
      var callback = function () {
        replaceBelow(term, subsForDash);
        takeBearings();
      };
      var description = render(term);
      navigate.on(name, callback, description);
    };

    var searchGlobals = function () {
      var names = corpus.findAllNames();
      var accept = function (name) {
        assert(name !== undefined);
        replaceBelow(VAR(name));
        takeBearings();
      };
      var cancel = takeBearings;
      navigate.search(names, accept, cancel);
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
        on('backspace', HOLE); // TODO define context-specific deletions
        navigate.on('/', searchGlobals, render(VAR('global.variable')));
        on('T', TOP);
        on('_', BOT);
        on('\\', LAMBDA(fresh, CURSOR(HOLE)));
        on('W', LETREC(fresh, CURSOR(HOLE), HOLE));
        on('L', LETREC(fresh, HOLE, CURSOR(HOLE)));
        on('space', APP(HOLE, CURSOR(HOLE)));
        on('(', APP(CURSOR(HOLE), HOLE));
        on('|', JOIN(CURSOR(HOLE), HOLE));
        on('{', QUOTE(CURSOR(HOLE)));

        var locals = ast.getBoundAbove(term);
        locals.forEach(function(varName){
          on(varName, VAR(varName));
          // TODO deal with >26 variables
        });

      } else {
        var dumped = ast.dump(term);

        // TODO define context-specific deletions
        on('backspace', HOLE);

        on('\\', LAMBDA(fresh, CURSOR(DASH)), dumped);
        on('W', LETREC(fresh, CURSOR(HOLE), DASH), dumped);
        on('L', LETREC(fresh, DASH, CURSOR(HOLE)), dumped);
        on('space', APP(DASH, CURSOR(HOLE)), dumped);
        on('(', APP(CURSOR(HOLE), DASH), dumped);
        on('|', JOIN(DASH, CURSOR(HOLE)), dumped);
        on('{', QUOTE(CURSOR(DASH)), dumped);
      }
    };
  })();

  //--------------------------------------------------------------------------
  // Interface

  return {
    main: function () {
      loadAllLines();
      renderAllLines();
      initCursor();
      takeBearings();
      $(window).off('keydown').on('keydown', navigate.trigger);
    },
  };
});
