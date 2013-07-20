/** 
 * Transforms : string <-> ugly tree <-> pretty tree
 */

define(['log', 'test', 'pattern'],
function(log,   test,   pattern)
{
  var compiler = {};

  //--------------------------------------------------------------------------
  // Parse

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

    var Parser = function (tokens) {
      if (_.isString(tokens)) {
        tokens = tokens.split(' ');
      }
      this.tokens = tokens;
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
  // Serialize

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

  test('ast.parse', function(){
    var cases = [
      'VAR x',
      'QUOTE APP LAMBDA CURSOR VAR x VAR x HOLE',
      'LET VAR i LAMBDA VAR x VAR x APP VAR i VAR i',
    ];
    for (var i = 0; i < cases.length; ++i) {
      var string = cases[i];
      log('Parsing ' + string);
      var expr = parse(string);
      var actualString = print(expr);
      assert.equal(string, actualString);
    }
  });

  //--------------------------------------------------------------------------
  // Symbols

  var Symbol = function (name, arity, parser) {
    arity = arity || 0;
    parse.declareSymbol(name, arity, parser);
    var symbol;
    if (arity == 0) {
      symbol = name;
    } else {
      symbol = function () {
        assert.equal(arguments.length, arity);
        return [name].concat(_.toArray(arguments));
      };
      symbol.name = name;
    }
    //compiler[name] = symbol;
    return symbol;
  };

  var TOP = Symbol('TOP');
  var BOT = Symbol('BOT');
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
  var VAR = Symbol('VAR', 1, function(tokens){
    var name = tokens.pop();
    return ['VAR', name];
  });
  var APP = Symbol('APP', 2);
  var COMP = Symbol('COMP', 2);
  var JOIN = Symbol('JOIN', 2);
  var RAND = Symbol('RAND', 2);
  var LAMBDA = Symbol('LAMBDA', 2);
  var DEFINE = Symbol('DEFINE', 2);
  var LET = Symbol('LET', 3);

  var STACK = Symbol('STACK', 2);
  var stack = (function(){
    var pop = Array.prototype.pop;
    var head = 'STACK';
    return function () {
      var tail = pop.call(arguments);
      while (arguments.length) {
        tail = [head, pop.call(arguments), tail];
      }
      return tail;
    };
  })();

  test('compiler.stack', function(){
    assert.equal(
      stack('x', 'y', 'z', []),
      STACK('x', STACK('y', STACK('z', []))));
  });

  //--------------------------------------------------------------------------
  // Convert : appTree <-> stack

  var toStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var tail = pattern.variable('tail');
    var t = pattern.match([
      APP(x, y), function (matched, tail) {
        return t(matched.x, STACK(matched.y, tail));
      },
      x, function (matched, tail) {
        return STACK(matched.x, tail)
      }
    ]);
    return function (appTree, tail) {
      if (tail === undefined) {
        tail = [];
      }
      return t(appTree, tail);
    };
  })();

  var fromStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var tail = pattern.variable('tail');
    var t = pattern.match([
      stack(x, y, tail), function (matched) {
        return t(stack(APP(matched.x, matched.y), matched.tail));
      },
      stack(x, []), function (matched) {
        return matched.x;
      }
    ]);
    return t;
  })();

  test('compiler.toStack, compiler.fromStack', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [I, stack(I, [])],
      [APP(x, y), stack(x, y, [])],
      [APP(APP(x, y), z), stack(x, y, z, [])],
      [APP(APP(APP(B, APP(K, x)), y), z), stack(B, APP(K, x), y, z, [])]
    ];
    examples.forEach(function(pair){
      assert.equal(toStack(pair[0]), pair[1]);
      assert.equal(fromStack(pair[1]), pair[0]);
    });
  });

  //--------------------------------------------------------------------------
  // Simplify : appTree -(-> stack -> stack -)-> appTree

  var simplify = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var tail = pattern.variable('tail');

    var simplifyStack = pattern.match([
      stack(BOT, tail), function (matched) {
        return stack(BOT, []);
      },
      stack(TOP, tail), function (matched) {
        return stack(TOP, []);
      },
      stack(I, x, tail), function (matched) {
        var step = stack(matched.x, matched.tail);
        return simplifyStack(step);
      },
      stack(K, x, y, tail), function (matched) {
        var step = stack(matched.x, matched.tail);
        return simplifyStack(step);
      },
      stack(B, x, y, z, tail), function (matched) {
        var xy = APP(matched.x, matched.y);
        var tail = stack(matched.z, matched.tail);
        var step = toStack(xy, tail);
        return simplifyStack(step);
      },
      stack(C, x, y, z, tail), function (matched) {
        var xz = APP(matched.x, matched.z);
        var tail = stack(matched.y, matched.tail);
        var step = toStack(xz, tail);
        return simplifyStack(step);
      },
      stack(x, tail), function (matched) {
        var tail = simplifyArgs(matched.tail);
        return stack(matched.x, tail);
      }
    ]);

    var simplifyArgs = pattern.match([
      stack(x, y), function (matched) {
        var rx = simplify(matched.x);
        var ry = simplifyArgs(matched.y);
        return stack(rx, ry);
      },
      [], function () {
        return [];
      }
    ]);

    var simplify = function (appTree) {
      if (_.isString(appTree)) {
        return appTree;
      } else {
        return fromStack(simplifyStack(toStack(appTree)));
      }
    };

    return simplify;
  })();

  test('compiler.simplify', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [APP(BOT, x), BOT],
      [APP(TOP, x), TOP],
      [APP(APP(K, x), y), x],
      [APP(APP(APP(B, x), y), z), APP(APP(x, y), z)],
      [APP(APP(APP(C, x), y), z), APP(APP(x, z), y)],
      [APP(APP(APP(B, APP(K, x)), y), z),
       APP(x, z)],
      [APP(APP(B, APP(I, x)), APP(APP(K, y), z)),
       APP(APP(B, x), y)]
    ];
    examples.forEach(function(pair){
      assert.equal(simplify(pair[0]), pair[1]);
    });
  });

  //--------------------------------------------------------------------------
  // Convert : appTree -> pretty

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
        return VAR(name);
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
      }
    ]);

    return function (ugly) {
      fresh.reset();
      return t(ugly);
    };
  })();

  test('compiler.decompile', function(){
    var a = VAR('a');
    var b = VAR('b');
    var c = VAR('c');
    var examples = [
      [I, LAMBDA(a, a)],
      [K, LAMBDA(a, LAMBDA(b, a))]
    ];
    examples.forEach(function(pair){
      assert.equal(decompile(pair[0]), pair[1]);
    });
  });

  return compiler;
});
