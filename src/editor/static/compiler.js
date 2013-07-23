/** 
 * Syntactic Transforms.
 *
 * appTree is the lingua franca.
 */

define(['log', 'test', 'pattern', 'symbols'],
function(log,   test,   pattern,   symbols)
{
  var compiler = {};

  //--------------------------------------------------------------------------
  // Parse

  var parse = compiler.parse = (function(){

    var parseSymbol = {};

    var symbolParser = function (name, arity) {
      if (arity == 0) {
        return function (parser) {
          return name;
        };
      } else {
        return function (parser) {
          var parsed = [name];
          for (var i = 0; i < arity; ++i) {
            parsed.push(parser.parse());
          }
          return parsed;
        };
      }
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

  var parseLine = compiler.parseLine = function (line) {
    var name = line.name;
    var body = parse(line.code);
    if (name !== null) {
      return DEFINE(name, body);
    } else {
      return ASSERT(body);
    }
  };
  
  //--------------------------------------------------------------------------
  // Serialize

  var print = compiler.print = (function(){
    var pushTokens = function (tokens, expr) {
      if (_.isString(expr)) {
        tokens.push(expr);
      } else {
        tokens.push(expr[0]);
        for (var i = 1; i < expr.length; ++i) {
          pushTokens(tokens, expr[i]);
        }
      }
    };
    return function (expr) {
      var tokens = [];
      pushTokens(tokens, expr);
      return tokens.join(' ');
    };
  })();

  test('ast.parse', function(){
    var examples = [
      'VAR x',
      'QUOTE APP LAMBDA CURSOR VAR x VAR x HOLE',
      'LET VAR i LAMBDA VAR x VAR x APP VAR i VAR i',
    ];
    assert.inverses(parse, print, examples);
  });

  //--------------------------------------------------------------------------
  // Symbols

  var symbols = compiler.symbols = {};
  var Symbol = function (name, arity, parser) {
    arity = arity || 0;
    parse.declareSymbol(name, arity, parser);
    var symbol;
    if (arity == 0) {
      symbol = name;
    } else {
      var errorMessage = name + '(...) called with wrong number of arguments';
      symbol = function () {
        assert.equal(arguments.length, arity, errorMessage);
        return [name].concat(_.toArray(arguments));
      };
      symbol.name = name;
      symbol.arity = arity;
    }
    compiler.symbols[name] = symbol;
    return symbol;
  };

  var TOP = Symbol('TOP');
  var BOT = Symbol('BOT');
  var I = Symbol('I');
  var K = Symbol('K');
  var B = Symbol('B');
  var C = Symbol('C');
  var CI = Symbol('CI');
  var CB = Symbol('CB');
  var W = Symbol('W');
  var S = Symbol('S');
  var Y = Symbol('Y');
  var U = Symbol('U');
  var V = Symbol('V');
  var P = Symbol('P');
  var A = Symbol('A');
  var J = Symbol('J');
  var R = Symbol('R');
  var QLESS = Symbol('QLESS');
  var QNLESS = Symbol('QNLESS');
  var QEQUAL = Symbol('QEQUAL');
  var HOLE = Symbol('HOLE');
  var QUOTE = Symbol('QUOTE', 1);
  var CURSOR = Symbol('CURSOR', 1);
  var ASSERT = Symbol('ASSERT', 1);
  var VAR = Symbol('VAR', 1, function(tokens){
    var name = tokens.pop();
    //assert(symbols.isGlobal(name), 'bad global: ' + name);
    return ['VAR', name];
  });
  var APP = Symbol('APP', 2);
  var COMP = Symbol('COMP', 2);
  var JOIN = Symbol('JOIN', 2);
  var RAND = Symbol('RAND', 2);
  var LAMBDA = Symbol('LAMBDA', 2);
  var DEFINE = Symbol('DEFINE', 2, function(tokens){
    var name = tokens.pop();  // now VAR(...) wrapper
    var body = tokens.parse();
    assert(symbols.isGlobal(name), 'bad global: ' + name);
    return ['DEFINE', name, body];
  });
  var STACK = Symbol('STACK', 2);
  var LET = Symbol('LET', 3);
  var LESS = Symbol('LESS', 2);
  var NLESS = Symbol('NLESS', 2);
  var EQUAL = Symbol('EQUAL', 2);

  var app = function (term) {
    for (var i = 1; i < arguments.length; ++i) {
      term = ['APP', term, arguments[i]];
    }
    return term;
  };

  test('compiler.app', function(){
    assert.equal(
      app('w', 'x', 'y', 'z'),
      APP(APP(APP('w', 'x'), 'y'), 'z'));
  });

  var stack = (function(){
    var pop = Array.prototype.pop;
    return function () {
      var tail = pop.call(arguments);
      while (arguments.length) {
        tail = ['STACK', pop.call(arguments), tail];
      }
      return tail;
    };
  })();

  test('compiler.stack', function(){
    assert.equal(
      stack('x', 'y', 'z', []),
      STACK('x', STACK('y', STACK('z', []))));
  });

  compiler.DEFINE = DEFINE;

  //--------------------------------------------------------------------------
  // Lingua Franca

  var isAppTree = compiler.isAppTree = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var t = pattern.match([
      APP(x, y), function (matched) {
        return t(matched.x) && t(matched.y);
      },
      QUOTE(x), function (matched) {
        return t(matched.x);
      },
      VAR(x), function (matched) {
        return true;
      },
      x, function (matched) {
        return _.isString(matched.x);
      }
    ]);
    return t;
  })();

  test('compiler.isAppTree', function () {
    var examples = [
      [APP(K, I), true],
      [QUOTE(K), true],
      [VAR('x'), true],
      [COMP(K, I), false],
      [LET(VAR('x'), I, I), false],
      [APP(COMP(I, I), I), false],
      [QUOTE(COMP(I, I)), false]
    ];
    assert.forward(isAppTree, examples);
  });

  //--------------------------------------------------------------------------
  // Conversion : appTree <-> code

  var fromCode = compiler.fromCode = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var t = pattern.match([
      APP(x, y), function (matched) {
        return APP(t(matched.x), t(matched.y));
      },
      COMP(x, y), function (matched) {
        return app(B, t(matched.x),  t(matched.y));
      },
      JOIN(x, y), function (matched) {
        return app(J, t(matched.x),  t(matched.y));
      },
      RAND(x, y), function (matched) {
        return app(R, t(matched.x),  t(matched.y));
      },
      QUOTE(x), function (matched) {
        return QUOTE(t(matched.x));
      },
      LESS(x, y), function (matched) {
        return app(QLESS, QUOTE(matched.x), QUOTE(matched.y));
      },
      NLESS(x, y), function (matched) {
        return app(QNLESS, QUOTE(matched.x), QUOTE(matched.y));
      },
      EQUAL(x, y), function (matched) {
        return app(QEQUAL, QUOTE(matched.x), QUOTE(matched.y));
      },
      x, function (matched) {
        return matched.x;
      }
    ]);
    return t;
  })();

  var toCode = compiler.toCode = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var t = pattern.match([
      app(B, x, y), function (matched) {
        return COMP(t(matched.x), t(matched.y));
      },
      app(J, x, y), function (matched) {
        return JOIN(t(matched.x), t(matched.y));
      },
      app(R, x, y), function (matched) {
        return RAND(t(matched.x), t(matched.y));
      },
      app(C, I), function () {
        return CI;
      },
      app(C, B), function () {
        return CB;
      },
      app(QLESS, QUOTE(x), QUOTE(y)), function (matched) {
        return LESS(matched.x, matched.y);
      },
      app(QNLESS, QUOTE(x), QUOTE(y)), function (matched) {
        return NLESS(matched.x, matched.y);
      },
      app(QEQUAL, QUOTE(x), QUOTE(y)), function (matched) {
        return EQUAL(matched.x, matched.y);
      },
      app(x, y), function (matched) {
        return app(t(matched.x), t(matched.y));
      },
      QUOTE(x), function (matched) {
        return QUOTE(t(matched.x));
      },
      x, function (matched) {
        return matched.x;
      }
    ]);
    return t;
  })();

  test('compiler.fromCode, compiler.toCode', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [app(x, y), app(x, y)],
      [COMP(x, y), app(B, x, y)],
      [JOIN(x, y), app(J, x, y)],
      [RAND(x, y), app(R, x, y)],
      [LESS(x, y), app(QLESS, QUOTE(x), QUOTE(y))],
      [NLESS(x, y), app(QNLESS, QUOTE(x), QUOTE(y))],
      [EQUAL(x, y), app(QEQUAL, QUOTE(x), QUOTE(y))],
      [app(COMP(x, y), COMP(y, z)), app(B, x, y, app(B, y, z))],
      [QUOTE(COMP(x, y)), QUOTE(app(B, x, y))]
    ];
    assert.forward(fromCode, examples);
    assert.backward(toCode, examples);
  });

  //--------------------------------------------------------------------------
  // Convert : appTree <-> stack

  var toStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var tail = pattern.variable('tail');
    var t = pattern.match([
      app(x, y), function (matched, tail) {
        return t(matched.x, stack(matched.y, tail));
      },
      x, function (matched, tail) {
        return stack(matched.x, tail)
      }
    ]);
    var pop = Array.prototype.pop;
    var head = 'STACK';
    return function (appTree) {
      var tail;
      if (arguments.length === 1) {
        tail = [];
      } else {
        tail = pop.call(arguments);
      }
      while (arguments.length > 1) {
        tail = [head, pop.call(arguments), tail];
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
        return t(stack(app(matched.x, matched.y), matched.tail));
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
      [app(x, y), stack(x, y, [])],
      [app(x, y, z), stack(x, y, z, [])],
      [app(S, app(K, x), y, z), stack(S, app(K, x), y, z, [])]
    ];
    assert.forward(toStack, examples);
    assert.backward(fromStack, examples);
  });

  //--------------------------------------------------------------------------
  // Simplify :   stack -> simple stack
  //            appTree -> simple appTree

  var simplifyStack = compiler.simplifyStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var tail = pattern.variable('tail');

    var simplifyStack = pattern.match([
      stack(TOP, tail), function (matched) {
        return stack(TOP, []);
      },
      stack(BOT, tail), function (matched) {
        return stack(BOT, []);
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
        var yz = app(matched.y, matched.z);
        var step = toStack(matched.x, yz, matched.tail);
        return simplifyStack(step);
      },
      stack(C, x, y, z, tail), function (matched) {
        var step = toStack(matched.x, matched.z, matched.y, matched.tail);
        return simplifyStack(step);
      },
      stack(W, x, VAR(name), tail), function (matched) {
        var y = VAR(name);
        var step = toStack(matched.x, y, y, matched.tail);
        return simplifyStack(step);
      },
      stack(S, x, y, VAR(name), tail), function (matched) {
        var z = VAR(name);
        var yz = app(matched.y, z);
        var step = toStack(matched.x, z, yz, matched.tail);
        return simplifyStack(step);
      },
      stack(J, TOP, tail), function (matched) {
        return stack(TOP, []);
      },
      stack(J, x, TOP, tail), function (matched) {
        return stack(TOP, []);
      },
      stack(J, BOT, tail), function (matched) {
        var step = stack(I, tail);
        return simplifyStack(step);
      },
      stack(J, x, BOT, tail), function (matched) {
        var step = stack(x, tail);
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

    return simplifyStack;
  })();

  var simplify = compiler.simplify = function (appTree) {
    if (_.isString(appTree)) {
      return appTree;
    } else {
      return fromStack(simplifyStack(toStack(appTree)));
    }
  };

  test('compiler.simplify', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [app(BOT, x), BOT],
      [app(TOP, x), TOP],
      [app(K, x, y), x],
      [app(B, x, y, z), app(x, app(y, z))],
      [app(C, x, y, z), app(x, z, y)],
      [app(B, x, app(K, y), z), app(x, y)],
      [app(B, app(I, x), app(K, y, z)), app(B, x, y)]
    ];
    assert.forward(simplify, examples);
  });

  //--------------------------------------------------------------------------
  // Convert : simple appTree -> lambda

  var toLambda = compiler.decomple = (function(){

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
    var tail = pattern.variable('tail');
    var name = pattern.variable('name');

    var stackToLambda = pattern.match([
      stack(TOP, []), function () { 
        return TOP;
      },
      stack(BOT, []), function () { 
        return BOT;
      },
      stack(I, []), function () {
        var x = fresh();
        return LAMBDA(x, x);
      },
      stack(K, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, x));
      },
      stack(K, x, []), function (matched) {
        var y = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, tx);
      },
      // TODO simplify B, C, W, S cases with a popFresh(cb) function
      stack(B, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, app(y, z)))));
      },
      stack(B, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, app(tx, app(y, z))));
      },
      stack(B, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, app(tx, app(ty, z)));
      },
      stack(C, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, z, y))));
      },
      stack(C, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, app(tx, z, y)));
      },
      stack(C, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, app(tx, z, ty));
      },
      stack(W, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, app(x, y, y)));
      },
      stack(W, x, []), function (matched) {
        var y = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, app(tx, y, y));
      },
      stack(W, x, VAR(name), tail), function (matched) {
        var y = VAR(matched.name);
        var head = toLambda(app(matched.x, y, y));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(W, x, y, tail), function (matched) {
        var y = fresh();
        var ty = toLambda(matched.y);
        var head = LET(y, ty, toLambda(app(matched.x, y, y)));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, z, app(y, z)))));
      },
      stack(S, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, app(tx, z, app(y, z))));
      },
      stack(S, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, app(tx, z, app(ty, z)));
      },
      stack(S, x, y, VAR(name), tail), function (matched) {
        var z = VAR(matched.name);
        var head = toLambda(app(matched.x, z, app(matched.y, z)));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, x, y, z, tail), function (matched) {
        var z = fresh();
        var tz = toLambda(matched.z);
        var xz = app(matched.x, z);
        var yz = app(matched.y, z);
        var head = LET(z, tz, toLambda(app(xz, yz)));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(J, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, JOIN(x, y)));
      },
      stack(J, x, []), function (matched) {
        var y = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, JOIN(tx, y));
      },
      stack(J, x, y, tail), function (matched) {
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        var head = JOIN(tx, ty);
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(R, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, RAND(x, y)));
      },
      stack(R, x, []), function (matched) {
        var y = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, RAND(tx, y));
      },
      stack(R, x, y, tail), function (matched) {
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        var head = RAND(tx, ty);
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(QUOTE(x), tail), function (matched) {
        var head = QUOTE(toLambda(matched.x));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(VAR(name), tail), function (matched) {
        var head = VAR(matched.name);
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      }
    ]);

    var argsToLambda = pattern.match([
      stack(x, y), function (matched) {
        var rx = toLambda(matched.x);
        var ry = argsToLambda(matched.y);
        return stack(rx, ry);
      },
      [], function () {
        return [];
      }
    ]);

    var toLambda = function (simpleAppTree) {
      fresh.reset();
      return stackToLambda(toStack(simpleAppTree));
    };

    return toLambda;
  })();

  //--------------------------------------------------------------------------
  // Abstract : varName x appTree -> appTree

  var lambda = compiler.lambda = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var notFound = {};

    var curriedLambda = _.memoize(function (varName) {
      var t = pattern.match([
        VAR(varName), function (matched) {
          return I;
        },
        // TODO match J
        // TODO match R
        // TODO match QUOTE
        app(x, VAR(varName)), function (matched) {
          var tx = t(matched.x);
          if (tx === notFound) {
            return matched.x;
          } else {
            return app(W, tx);
          }
        },
        app(x, y), function (matched) {
          var tx = t(matched.x);
          var ty = t(matched.y);
          if (tx === notFound) {
            if (ty === notFound) {
              return notFound;
            } else {
              return app(B, matched.x, ty);
            }
          } else {
            if (ty === notFound) {
              return app(C, tx, matched.y);
            } else {
              return app(S, tx, ty);
            }
          }
        },
        x, function () {
          return notFound;
        }
      ]);
      return t;
    });
    return function (varName, term) {
      var result = curriedLambda(varName)(term);
      if (result === notFound) {
        return app(K, term);
      } else {
        return result;
      }
    };
  })();

  test('compile.lambda', function () {
    var a = VAR('a');
    var x = VAR('x');
    var y = VAR('y');
    var lambdaA = _.partial(lambda, 'a');
    var examples = [
      [a, I],
      [app(x, a), x],
      [app(x, a, a), app(W, x)],
      [app(y, app(x, a)), app(B, y, x)],
      [app(x, a, y), app(C, x, y)],
      [app(x, a, app(x, a)), app(S, x, x)],
      [x, app(K,x)]
    ];
    assert.forward(lambdaA, examples);
  });

  //--------------------------------------------------------------------------
  // Convert : lambda -> appTree

  var fromLambda = compiler.fromLambda = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var name = pattern.variable('name');

    var t = pattern.match([
      app(x, y), function (matched) {
        return app(t(matched.x), t(matched.y));
      },
      LAMBDA(VAR(name), x), function (matched) {
        return lambda(matched.name, t(matched.x));
      },
      LET(VAR(name), x, y), function (matched) {
        return app(lambda(matched.name, t(matched.y)), t(matched.x));
      },
      JOIN(x, y), function (matched) {
        return app(J, t(matched.x),  t(matched.y));
      },
      RAND(x, y), function (matched) {
        return app(R, t(matched.x),  t(matched.y));
      },
      QUOTE(x), function (matched) {
        return QUOTE(t(matched.x));
      },
      x, function (matched) {
        return matched.x;
      }
    ]);
    return t;
  })();

  test('compiler.toLambda, compiler.fromLambda', function(){
    var a = VAR('a');
    var b = VAR('b');
    var c = VAR('c');
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var xy = app(x, y);  // just something that is not a variable
    var examples = [
      [TOP, TOP],
      [BOT, BOT],
      [I, LAMBDA(a, a)],
      [K, LAMBDA(a, LAMBDA(b, a))],
      [app(K, x), LAMBDA(a, x)],
      [B, LAMBDA(a, LAMBDA(b, LAMBDA(c, app(a, app(b, c)))))],
      [app(B, x), LAMBDA(a, LAMBDA(b, app(x, app(a, b))))],
      [app(B, x, y), LAMBDA(a, app(x, app(y, a)))],
      [C, LAMBDA(a, LAMBDA(b, LAMBDA(c, app(a, c, b))))],
      [app(C, x), LAMBDA(a, LAMBDA(b, app(x, b, a)))],
      [app(C, x, y), LAMBDA(a, app(x, a, y))],
      [W, LAMBDA(a, LAMBDA(b, app(a, b, b)))],
      [app(W, x), LAMBDA(a, app(x, a, a))],
      [app(W, x, xy), LET(a, xy, app(x, a, a))],
      [S, LAMBDA(a, LAMBDA(b, LAMBDA(c, app(a, c, app(b, c)))))],
      [app(S, x), LAMBDA(a, LAMBDA(b, app(x, b, app(a, b))))],
      [app(S, x, y), LAMBDA(a, app(x, a, app(y, a)))],
      [app(S, x, y, xy), LET(a, xy, app(x, a, app(y, a)))],
      [J, LAMBDA(a, LAMBDA(b, JOIN(a, b)))],
      [app(J, x), LAMBDA(a, JOIN(x, a))],
      [app(J, x, y), JOIN(x, y)],
      [app(J, x, y, I), app(JOIN(x, y), LAMBDA(a, a))],
      [R, LAMBDA(a, LAMBDA(b, RAND(a, b)))],
      [app(R, x), LAMBDA(a, RAND(x, a))],
      [app(R, x, y), RAND(x, y)],
      [app(R, x, y, I), app(RAND(x, y), LAMBDA(a, a))],
      [QUOTE(I), QUOTE(LAMBDA(a, a))],
      [app(QUOTE(x), I), app(QUOTE(x), LAMBDA(a, a))],
      [VAR(x), VAR(x)],
      [app(VAR(x), I), app(VAR(x), LAMBDA(a, a))],
    ];
    assert.forward(toLambda, examples);
    assert.backward(fromLambda, examples);
  });

  test('compiler.toLambda', function(){
    // fromLambda would fail these because they involve pattern matching
    var a = VAR('a');
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var xy = app(x, y);  // just something that is not a variable
    var examples = [
      [app(W, x, y), app(x, y, y)],
      [app(W, x, y, I), app(x, y, y, LAMBDA(a, a))],
      [app(S, x, y, z), app(x, z, app(y, z))],
      [app(S, x, y, z, I), app(x, z, app(y, z), LAMBDA(a, a))]
    ];
    assert.forward(toLambda, examples);
  });

  test('compiler.fromLambda', function () {
    // toLamda would fail these because input is not simple
    var a = VAR('a');
    var x = VAR('x');
    var examples = [
      [app(LAMBDA(a, a), x), app(I, x)]
    ];
    assert.forward(fromLambda, examples);
  });

  return compiler;
});
