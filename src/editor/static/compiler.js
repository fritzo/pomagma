/** 
 * Abstract syntax trees
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

// FIXME why does "define([], function(){...})" not work here?
define(['log', 'test', 'pattern'],
function(log,   test,   pattern)
{
  var compiler = {};

  //--------------------------------------------------------------------------
  // Parsing

  var parse = compiler.parse = (function(){

    var parseSymbol = {};

    var symbolParser = function (name, arity) {
      return function (parser) {
        var parsed = [name];
        for (var i = 0; i < arity; ++i) {
          parsed.push(parser.parse());
        }
        return parsed;
      };
    };

    var Parser = function (string) {
      this.tokens = string.split(' ');
      this.pos = 0;
    };

    Parser.prototype.pop = function () {
      return this.tokens[this.pos++];
    };

    Parser.prototype.parse = function () {
      var head = this.pop();
      var parser = parseSymbol[head];
      assert(parser !== undefined, 'unrecognized token: ' + head);
      return parser(this);
    };

    var parse = function (string) {
      var parser = new Parser(string);
      return parser.parse();
    };

    parse.declareSymbol = function (name, arity, parser) {
      assert(parseSymbol[name] === undefined, 'duplicate symbol: ' + name);
      parseSymbol[name] = parser || symbolParser(name, arity);
    };

    return parse;
  })();

  //--------------------------------------------------------------------------
  // Symbols

  var Symbol = function (name, arity, parser) {
    arity = arity || 0;
    parse.declareSymbol(name, arity, parser);
    return function () {
      assert.equal(arguments.length, arity);
      return [name].concat(_.toArray(arguments));
    };
  };

  var I = Symbol('I');
  var K = Symbol('K');
  var B = Symbol('B');
  var C = Symbol('C');
  var W = Symbol('W');
  var S = Symbol('S');
  var J = Symbol('J');
  var R = Symbol('R');
  var HOLE = Symbol('HOLE');
  var QUOTE = Symbol('QUOTE', 1);
  var CURSOR = Symbol('CURSOR', 1);
  var ASSERT = Symbol('ASSERT', 1);
  var VARY = Symbol('VARY', 1, function(tokens){
    return ['VARY', tokens.pop()];
  });
  var APP = Symbol('APP', 2);
  var COMP = Symbol('COMP', 2);
  var JOIN = Symbol('JOIN', 2);
  var RAND = Symbol('RAND', 2);
  var LAMBDA = Symbol('LAMBDA', 2);
  var DEFINE = Symbol('DEFINE', 2);
  var LET = Symbol('LET', 3);

  //--------------------------------------------------------------------------
  // Decompiling

  var decompile = compiler.decomple = (function(){

    var fresh = (function(){
      var alphabet = 'abcdefghijklmnopqrstuvwxyz';
      var count = 0;
      var fresh = function () {
        var name = alphabet[count % alphabet.length];
        var number = Math.floor(count / alphabet.length);
        if (number > 0) {
          name += number;
        }
        count += 1;
        return VARY(name);
      };
      fresh.reset = function () {
        count = 0;
      };
      return fresh;
    })();

    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');

    var t = pattern.match([
      I, function () {
        var x = fresh();
        return LAMBDA(x, x);
      },
      APP(I, x), function (matched) {
        return t(matched.x);
      },
      K, function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, x));
      },
      APP(K, x), function (matched) {
        var y = fresh();
        var tx = t(matched.x);
        return LAMBDA(y, tx);
      },
      APP(APP(K, x), y), function (matched) {
        return t(matched.x);
      },
      S, function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, APP(APP(x, z), APP(y, z)))));
      },
      APP(S, x), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = t(matched.x);
        return LAMBDA(y, LAMBDA(z, APP(APP(tx, z), APP(y, z))));
      },
      APP(APP(S, x), y), function (matched) {
        var z = fresh();
        var tx = t(matched.x);
        var ty = t(matched.y);
        return LAMBDA(z, APP(APP(tx, z), APP(ty, z)));
      },
      APP(APP(APP(S, x), y), z), function (matched) {
        var x = matched.x;
        var y = matched.y;
        var z = fresh();
        var tz = t(matched.z);
        var txy = t(APP(APP(x, z), APP(y, z)));  // FIXME infinite loop
        return LET(z, tz, txy);
      },
      J, function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, JOIN(x, y)));
      },
      APP(J, x), function (matched) {
        var y = fresh();
        var tx = t(matched.x);
        return LAMBDA(y, JOIN(tx, y));
      },
      APP(APP(J, x), y), function (matched) {
        var tx = t(matched.x);
        var ty = t(matched.y);
        return JOIN(tx, ty);
      },
      JOIN(x, y), function (matched) {
        var tx = t(matched.x);
        var ty = t(matched.y);
        return JOIN(tx, ty);
      },
      APP(x, y), function (matched) {
        // FIXME is this the right reduction order?
        var tx = t(matched.x);
        var ty = t(matched.y);
        return APP(tx, ty);
      },
      COMP(x, y), function (matched) {
        return t(APP(APP(B, matched.x), matched.y));
      },
      QUOTE(x), function (matched) {
        return QUOTE(t(matched.x));
      },
      x, function (matched) {
        throw 'failed to decompile: ' + JSON.stringify(matched.x);
      }
    ]);

    return function (ugly) {
      fresh.reset();
      return t(ugly);
    };
  })();

  test('decompile', function(){
    var ugly = ['B', ['x'], ['C', ['I']], ['K']];
    var pretty = null;
    assert.equal(decompile(ugly), pretty);
  });
  
  //--------------------------------------------------------------------------
  // Printing

  var print = compiler.print = (function(){
    var pushTokens = function (tokens, expr) {
      tokens.push(expr[0]);
      for (var i = 1; i < expr.length; ++i) {
        pushTokens(tokens, expr[i]);
      }
    };
    return function (expr) {
      var tokens = [];
      pushTokens(tokens, expr);
      return tokens.join(' ');
    };
  })();

  test('Simple parsing', function(){
    var cases = [
      'VARY x',
      'QUOTE APP LAMBDA CURSOR VARY x VARY x HOLE',
      'LET VARY i LAMBDA VARY x VARY x APP VARY i VARY i',
    ];
    for (var i = 0; i < cases.length; ++i) {
      var string = cases[i];
      log('Parsing ' + string);
      var expr = parse(string);
      var actualString = print(expr);
      assert.equal(string, actualString);
    }
  });

//----------------------------------------------------------------------------
// Construction

var Hole = function () {
  this.below = [];
  this.above = null;
};

var Vary = function (name) {
  this.name = name;
  this.below = [];
  this.above = null;
};

var Define = function (patt, defn) {
  this.below = [patt, defn];
  this.above = null;
  patt.above = this;
  defn.above = this;
};

var Let = function (patt, defn, body) {
  this.below = [patt, defn, body];
  this.above = null;
  patt.above = this;
  defn.above = this;
  body.above = this;
};

var Abstract = function (patt, body) {
  this.below = [patt, body];
  this.above = null;
  patt.above = this;
  body.above = this;
};

var Apply = function (fun, arg) {
  this.below = [fun, arg];
  this.above = null;
  fun.above = this;
  arg.above = this;
};

var Quote = function (body) {
  this.below = [body];
  this.above = null;
  body.above = this;
};

var Cursor = function (body) {
  this.below = [body];
  this.above = null;
  body.above = this;
};

//----------------------------------------------------------------------------
// Cursor movement

Cursor.prototype.remove = function () {
  var above = this.above;
  this.below[0].above = above;
  if (above) {
    var pos = above.below.indexOf(this);
    above.below[pos] = this.below[0];
    return pos;
  }
};

Cursor.prototype.insertBelow = function (above, pos) {
  var below = above.below[pos];
  above.below[pos] = this;
  this.above = above;
  below.above = this;
  this.below[0] = below;
};

Cursor.prototype.insertAbove = function (below) {
  this.below[0] = below;
  var above = below.above;
  below.above = this;
  this.above = above;
  if (above !== null) {
    var pos = above.below.indexOf(below);
    above.below.below[pos] = this;
  }
};

Cursor.prototype.tryMoveDown = function () {
  var pivot = this.below[0];
  if (pivot.below.length === 0) {
    return false;
  } else {
    this.remove();
    this.insertBelow(pivot, 0);
    return true;
  }
};

Cursor.prototype.tryMoveUp = function () {
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

Cursor.prototype.tryMoveSideways = function (direction) {
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

Cursor.prototype.tryMoveLeft = function () {
  return this.tryMoveSideways(-1);
};

Cursor.prototype.tryMoveRight = function () {
  return this.tryMoveSideways(+1);
};

Cursor.prototype.tryMove = function (direction) {
  switch (direction) {
    case 'U': return this.tryMoveUp();
    case 'L': return this.tryMoveLeft(); // || this.tryMoveUp();
    case 'D': return this.tryMoveDown(); // || this.tryMoveRight();
    case 'R': return this.tryMoveRight(); // || this.tryMoveDown();
  }
};

test('Cursor movement', function(){
  var string = 'LAMBDA QUOTE VARY this APP VARY is APP VARY a VARY test';
  log('Traversing ' + string)
  var expr = parse(string);
  var cursor = new Cursor(expr);
  var path =  'UDDDLRULDRDLDUUUU';
  var trace = '01100011111101110';
  for (var i = 0; i < path.length; ++i) {
    assert.equal(cursor.tryMove(path[i]), Boolean(parseInt(trace[i])));
  }
});

compiler.getRoot = function (expr) {
  while (expr.above !== null) {
    expr = expr.above;
  }
  return expr;
};

//----------------------------------------------------------------------------
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

Hole.prototype.lines = function () {
  return ['?'];
};

Vary.prototype.lines = function () {
  return [this.name];
};

Define.prototype.lines = function () {
  var patt = this.below[0];
  var defn = this.below[1];
  var pattLines = patt.lines();
  var defnLines = defn.lines(' ');
  assert(pattLines.length == 1, 'too many pattern lines: ' + pattLines);
  return [KEYWORDS['let'] + ' ' + pattLines[0] + ' ' + KEYWORDS['=']].concat(
    defnLines.map(indent));
};

Let.prototype.lines = function () {
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
    return [KEYWORDS['let'] + ' ' + pattLines[0] + ' ' + KEYWORDS['=']].concat(
      defnLines.map(indent),
      KEYWORDS['in'],
      body.lines().map(indent));
  }
};

Abstract.prototype.lines = function () {
  var patt = this.below[0];
  var body = this.below[1];
  var pattLines = patt.lines();
  assert(pattLines.length == 1, 'too many pattern lines: ' + pattLines);
  return [KEYWORDS['fun'] + ' ' + patt.lines()[0]].concat(body.lines());
};

Apply.prototype.lines = function () {
  var fun = this.below[0];
  var arg = this.below[1];
  var funLines = fun.lines();
  var argLines = arg.lines();
  assert(funLines.length == 1, 'too many function lines: ' + funLines);
  assert(argLines.length == 1, 'too many argument lines: ' + argLines);
  return [fun.lines() + ' ' +  arg.lines()];  // FIXME assumes associativity
};

Quote.prototype.lines = function () {
  var body = this.below[0];
  var bodyLines = body.lines();
  var end = bodyLines.length - 1;
  bodyLines[0] = '{' + bodyLines[0];
  bodyLines[end] = bodyLines[end] + '}';
  return bodyLines;
};

Cursor.prototype.lines = function () {
  var body = this.below[0];
  var bodyLines = body.lines();
  var end = bodyLines.length - 1;
  bodyLines[0] = '<span class=cursor>' + bodyLines[0];
  bodyLines[end] = bodyLines[end] + '</span>';
  return bodyLines;
};

//----------------------------------------------------------------------------
// Transformations

Hole.prototype.transform = {
  VARY: function (cursor) {
  }
};

Vary.transform = {
  HOLE: function (cursor) {
    
  }
};

  return compiler;
});
