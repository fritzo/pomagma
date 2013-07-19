/** 
 * LAMBDA syntax trees
 *
 *   expr ::= var
 *          | QUOTE expr
 *          | LET patt expr expr
 *            # allows recursion when fv(patt) appear in first expr
 *          | LAMBDA patt expr
 *          | APP expr expr
 *          | JOIN expr expr
 *          | COMP expr expr
 *          | BOX expr
 *          | HOLE
 *          | CURSOR expr
 *
 *   patt ::= var
 *          | QUOTE patt
 *          | BOX patt
 *          | TYPE patt expr
 *          | CURSOR patt
 */

define(['log', 'test'],
function(log,   test)
{
  var ast = {};

  //--------------------------------------------------------------------------
  // Construction

  var constructors = {};
  var Constructor = function (fun) {
    constructors[fun.name] = fun;
    return fun;
  };

  var HOLE = Constructor(function HOLE () {
    this.below = [];
    this.above = null;
  });

  var VAR = Constructor(function VAR (name) {
    this.name = name;
    this.below = [];
    this.above = null;
  });

  var DEFINE = Constructor(function DEFINE (patt, defn) {
    this.below = [patt, defn];
    this.above = null;
    patt.above = this;
    defn.above = this;
  });

  var LET = Constructor(function LET (patt, defn, body) {
    this.below = [patt, defn, body];
    this.above = null;
    patt.above = this;
    defn.above = this;
    body.above = this;
  });

  var LAMBDA = Constructor(function LAMBDA (patt, body) {
    this.below = [patt, body];
    this.above = null;
    patt.above = this;
    body.above = this;
  });

  var APP = Constructor(function APP (fun, arg) {
    this.below = [fun, arg];
    this.above = null;
    fun.above = this;
    arg.above = this;
  });

  var QUOTE = Constructor(function QUOTE (body) {
    this.below = [body];
    this.above = null;
    body.above = this;
  });

  var CURSOR = Constructor(function CURSOR (body) {
    this.below = [body];
    this.above = null;
    body.above = this;
  });

  //--------------------------------------------------------------------------
  // Loading from tree format

  var load = ast.load = function (tree) {
    assert(_.isArray(tree), 'bad tree: ' + tree);
    //log('DEBUG ' + JSON.stringify(tree));
    var symbol = tree[0];
    var ctor = constructors[symbol];
    assert(ctor !== undefined, 'unrecognized symbol: ' + symbol);
    var args = [];
    if (symbol === 'VAR') {
      args = [tree[1]];
    } else {
      for (var i = 1; i < tree.length; ++i) {
        args.push(load(tree[i]));
      }
    }
    assert(args.length <= 3, 'arity not implemented: ' + args.length);
    return new ctor(args[0], args[1], args[2]);
  };

  test('ast.load', function(){
    var cases = [
      ['VAR', 'x'],
      ['QUOTE',
        ['APP',
          ['LAMBDA', ['CURSOR', ['VAR', 'x']], ['VAR', 'x']],
          ['HOLE']]],
      ['LET',
        ['VAR', 'i'],
        ['LAMBDA', ['VAR', 'x'], ['VAR', 'x']],
        ['APP', ['VAR', 'i'], ['VAR', 'i']]],
    ];
    for (var i = 0; i < cases.length; ++i) {
      var string = cases[i];
      log('Loading ' + string);
      var expr = load(string);
      var polish = expr.dump();
      assert.equal(string, polish);
    }
  });

  //--------------------------------------------------------------------------
  // Dumping to tree format

  HOLE.prototype.dump = function () {
    return ['HOLE'];
  };

  VAR.prototype.dump = function () {
    return ['VAR', this.name];
  };

  DEFINE.prototype.dump = function () {
    var patt = this.below[0];
    var defn = this.below[1];
    return ['DEFINE', patt.dump(), defn.dump()];
  };

  LET.prototype.dump = function () {
    var patt = this.below[0];
    var defn = this.below[1];
    var body = this.below[2];
    return ['LET', patt.dump(), defn.dump(), body.dump()];
  };

  LAMBDA.prototype.dump = function () {
    var patt = this.below[0];
    var body = this.below[1];
    return ['LAMBDA', patt.dump(), body.dump()];
  };

  APP.prototype.dump = function () {
    var fun = this.below[0];
    var arg = this.below[1];
    return ['APP', fun.dump(), arg.dump()];
  };

  QUOTE.prototype.dump = function () {
    var body = this.below[0];
    return ['QUOTE', body.dump()];
  };

  CURSOR.prototype.dump = function () {
    var body = this.below[0];
    return ['CURSOR', body.dump()];
  };

  //--------------------------------------------------------------------------
  // CURSOR movement

  CURSOR.prototype.remove = function () {
    var above = this.above;
    this.below[0].above = above;
    if (above) {
      var pos = above.below.indexOf(this);
      above.below[pos] = this.below[0];
      return pos;
    }
  };

  CURSOR.prototype.insertBelow = function (above, pos) {
    var below = above.below[pos];
    above.below[pos] = this;
    this.above = above;
    below.above = this;
    this.below[0] = below;
  };

  CURSOR.prototype.insertAbove = function (below) {
    this.below[0] = below;
    var above = below.above;
    below.above = this;
    this.above = above;
    if (above !== null) {
      var pos = above.below.indexOf(below);
      above.below.below[pos] = this;
    }
  };

  CURSOR.prototype.tryMoveDown = function () {
    var pivot = this.below[0];
    if (pivot.below.length === 0) {
      return false;
    } else {
      this.remove();
      this.insertBelow(pivot, 0);
      return true;
    }
  };

  CURSOR.prototype.tryMoveUp = function () {
    var pivot = this.above;
    if (pivot === null) {
      return false;
    } else {
      this.remove();
      var above = pivot.above;
      if (above === null) {
        this.insertAbove(pivot);
      } else {
        var pos = above.below.indexOf(pivot);
        this.insertBelow(above, pos);
      }
      return true;
    }
  };

  CURSOR.prototype.tryMoveSideways = function (direction) {
    var pivot = this.above;
    if ((pivot === null) || (pivot.below.length === 1)) {
      return false;
    } else {
      var pos = this.remove();
      pos = (pos + direction + pivot.below.length) % pivot.below.length;
      this.insertBelow(pivot, pos);
      return true;
    }
  };

  CURSOR.prototype.tryMoveLeft = function () {
    return this.tryMoveSideways(-1);
  };

  CURSOR.prototype.tryMoveRight = function () {
    return this.tryMoveSideways(+1);
  };

  CURSOR.prototype.tryMove = function (direction) {
    switch (direction) {
      case 'U': return this.tryMoveUp();
      case 'L': return this.tryMoveLeft(); // || this.tryMoveUp();
      case 'D': return this.tryMoveDown(); // || this.tryMoveRight();
      case 'R': return this.tryMoveRight(); // || this.tryMoveDown();
    }
  };

  test('ast.CURSOR movement', function(){
    var tree = ['LAMBDA',
      ['QUOTE', ['VAR', 'this']],
      ['APP', ['VAR', 'is'], ['APP', ['VAR', 'a'], ['VAR', 'test']]]];
    log('Traversing ' + JSON.stringify(tree))
    var expr = load(tree);
    var cursor = new CURSOR(expr);
    var path =  'UDDDLRULDRDLDUUUU';
    var trace = '01100011111101110';
    for (var i = 0; i < path.length; ++i) {
      assert.equal(cursor.tryMove(path[i]), Boolean(parseInt(trace[i])));
    }
  });

  ast.getRoot = function (expr) {
    while (expr.above !== null) {
      expr = expr.above;
    }
    return expr;
  };

  //--------------------------------------------------------------------------
  // Pretty printing

  var KEYWORDS = {
    'let': '<span class=keyword>let</span>',
    '=': '<span class=keyword>=</span>',
    'in': '<span class=keyword>in</span>',
    'fun': '<span class=keyword>fun</span>'
  };

  var indent = function (line) {
    return '    ' + line;
  };

  HOLE.prototype.lines = function () {
    return ['?'];
  };

  VAR.prototype.lines = function () {
    return [this.name];
  };

  DEFINE.prototype.lines = function () {
    var patt = this.below[0];
    var defn = this.below[1];
    var pattLines = patt.lines();
    var defnLines = defn.lines(' ');
    assert(pattLines.length == 1, 'too many pattern lines: ' + pattLines);
    return [KEYWORDS['let'] + ' ' + pattLines[0] + ' ' + KEYWORDS['=']].concat(
      defnLines.map(indent));
  };

  LET.prototype.lines = function () {
    var patt = this.below[0];
    var defn = this.below[1];
    var body = this.below[2];
    var pattLines = patt.lines();
    var defnLines = defn.lines(' ');
    assert(pattLines.length == 1, 'too many pattern lines: ' + pattLines);
    if (defnLines.length == 1) {
      return [KEYWORDS['let'] + ' ' + pattLines[0] + ' ' + KEYWORDS['='] +
        ' ' + defnLines[0] + ' ' + KEYWORDS['in']].concat(
        body.lines().map(indent));
    } else {
      return [
        KEYWORDS['let'] + ' ' + pattLines[0] + ' ' + KEYWORDS['=']
      ].concat(
        defnLines.map(indent),
        KEYWORDS['in'],
        body.lines().map(indent)
      );
    }
  };

  LAMBDA.prototype.lines = function () {
    var patt = this.below[0];
    var body = this.below[1];
    var pattLines = patt.lines();
    assert(pattLines.length == 1, 'too many pattern lines: ' + pattLines);
    return [KEYWORDS['fun'] + ' ' + patt.lines()[0]].concat(body.lines());
  };

  APP.prototype.lines = function () {
    var fun = this.below[0];
    var arg = this.below[1];
    var funLines = fun.lines();
    var argLines = arg.lines();
    assert(funLines.length == 1, 'too many function lines: ' + funLines);
    assert(argLines.length == 1, 'too many argument lines: ' + argLines);
    return [fun.lines() + ' ' +  arg.lines()];  // FIXME assumes associativity
  };

  QUOTE.prototype.lines = function () {
    var body = this.below[0];
    var bodyLines = body.lines();
    var end = bodyLines.length - 1;
    bodyLines[0] = '{' + bodyLines[0];
    bodyLines[end] = bodyLines[end] + '}';
    return bodyLines;
  };

  CURSOR.prototype.lines = function () {
    var body = this.below[0];
    var bodyLines = body.lines();
    var end = bodyLines.length - 1;
    bodyLines[0] = '<span class=cursor>' + bodyLines[0];
    bodyLines[end] = bodyLines[end] + '</span>';
    return bodyLines;
  };

  //--------------------------------------------------------------------------
  // Transformations

  HOLE.prototype.transform = {
    VAR: function (cursor) {
      TODO();
    }
  };

  VAR.transform = {
    HOLE: function (cursor) {
      TODO();
    }
  };

  return ast;
});
