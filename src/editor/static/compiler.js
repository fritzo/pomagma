/** 
 * Syntactic Transforms.
 *
 * appTree is the lingua franca.
 */

define(['log', 'test', 'pattern', 'memoized'],
function(log,   test,   pattern,   memoized)
{
  var compiler = {};

  //--------------------------------------------------------------------------
  // Test Transforms

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
    var examples = [
      'VAR x',
      'QUOTE APP LAMBDA CURSOR VAR x VAR x HOLE',
      'LET VAR i LAMBDA VAR x VAR x APP VAR i VAR i',
    ];
    assert.inverses(parse, print, examples);
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
      var errorMessage = name + '(...) called with wrong number of arguments';
      symbol = function () {
        assert.equal(arguments.length, arity, errorMessage);
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
        return APP(APP(B, t(matched.x)),  t(matched.y));
      },
      JOIN(x, y), function (matched) {
        return APP(APP(J, t(matched.x)),  t(matched.y));
      },
      RAND(x, y), function (matched) {
        return APP(APP(R, t(matched.x)),  t(matched.y));
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

  var toCode = compiler.toCode = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var t = pattern.match([
      APP(APP(B, x), y), function (matched) {
        return COMP(t(matched.x), t(matched.y));
      },
      APP(APP(J, x), y), function (matched) {
        return JOIN(t(matched.x), t(matched.y));
      },
      APP(APP(R, x), y), function (matched) {
        return RAND(t(matched.x), t(matched.y));
      },
      APP(x, y), function (matched) {
        return APP(t(matched.x), t(matched.y));
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
      [APP(x, y), APP(x, y)],
      [COMP(x, y), APP(APP(B, x), y)],
      [JOIN(x, y), APP(APP(J, x), y)],
      [RAND(x, y), APP(APP(R, x), y)],
      [APP(COMP(x, y), COMP(y, z)), APP(APP(APP(B, x), y), APP(APP(B, y), z))],
      [QUOTE(COMP(x, y)), QUOTE(APP(APP(B, x), y))]
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
      APP(x, y), function (matched, tail) {
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
      [APP(APP(APP(S, APP(K, x)), y), z), stack(S, APP(K, x), y, z, [])]
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
        var yz = APP(matched.y, matched.z);
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
        var yz = APP(matched.y, z);
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
      [APP(BOT, x), BOT],
      [APP(TOP, x), TOP],
      [APP(APP(K, x), y), x],
      [APP(APP(APP(B, x), y), z), APP(x, APP(y, z))],
      [APP(APP(APP(C, x), y), z), APP(APP(x, z), y)],
      [APP(APP(APP(B, x), APP(K, y)), z), APP(x, y)],
      [APP(APP(B, APP(I, x)), APP(APP(K, y), z)), APP(APP(B, x), y)]
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
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, APP(x, APP(y, z)))));
      },
      stack(B, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, APP(tx, APP(y, z))));
      },
      stack(B, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, APP(tx, APP(ty, z)));
      },
      stack(C, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, APP(APP(x, z), y))));
      },
      stack(C, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, APP(APP(tx, z), y)));
      },
      stack(C, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, APP(APP(tx, z), ty));
      },
      stack(W, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, APP(APP(x, y), y)));
      },
      stack(W, x, []), function (matched) {
        var y = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, APP(APP(tx, y), y));
      },
      stack(W, x, VAR(name), tail), function (matched) {
        var y = VAR(matched.name);
        var xy = APP(matched.x, y);
        var head = toLambda(APP(xy, y));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(W, x, y, tail), function (matched) {
        var y = fresh();
        var ty = toLambda(matched.y);
        var xy = APP(matched.x, y);
        var head = LET(y, ty, toLambda(APP(xy, y)));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, APP(APP(x, z), APP(y, z)))));
      },
      stack(S, x, []), function (matched) {
        var y = fresh();
        var z = fresh();
        var tx = toLambda(matched.x);
        return LAMBDA(y, LAMBDA(z, APP(APP(tx, z), APP(y, z))));
      },
      stack(S, x, y, []), function (matched) {
        var z = fresh();
        var tx = toLambda(matched.x);
        var ty = toLambda(matched.y);
        return LAMBDA(z, APP(APP(tx, z), APP(ty, z)));
      },
      stack(S, x, y, VAR(name), tail), function (matched) {
        var z = VAR(matched.name);
        var xz = APP(matched.x, z);
        var yz = APP(matched.y, z);
        var head = toLambda(APP(xz, yz));
        var tail = argsToLambda(matched.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, x, y, z, tail), function (matched) {
        var z = fresh();
        var tz = toLambda(matched.z);
        var xz = APP(matched.x, z);
        var yz = APP(matched.y, z);
        var head = LET(z, tz, toLambda(APP(xz, yz)));
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

    var curriedLambda = memoized(function (varName) {
      var t = pattern.match([
        VAR(varName), function (matched) {
          return I;
        },
        // TODO match J
        // TODO match R
        // TODO match QUOTE
        APP(x, VAR(varName)), function (matched) {
          var tx = t(matched.x);
          if (tx === notFound) {
            return matched.x;
          } else {
            return APP(W, tx);
          }
        },
        APP(x, y), function (matched) {
          var tx = t(matched.x);
          var ty = t(matched.y);
          if (tx === notFound) {
            if (ty === notFound) {
              return notFound;
            } else {
              return APP(APP(B, matched.x), ty);
            }
          } else {
            if (ty === notFound) {
              return APP(APP(C, tx), matched.y);
            } else {
              return APP(APP(S, tx), ty);
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
        return APP(K, term);
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
      [APP(x, a), x],
      [APP(APP(x, a), a), APP(W, x)],
      [APP(y, APP(x, a)), APP(APP(B, y), x)],
      [APP(APP(x, a), y), APP(APP(C, x), y)],
      [APP(APP(x, a), APP(x, a)), APP(APP(S, x), x)],
      [x, APP(K,x)]
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
      APP(x, y), function (matched) {
        return APP(t(matched.x), t(matched.y));
      },
      LAMBDA(VAR(name), x), function (matched) {
        return lambda(matched.name, t(matched.x));
      },
      LET(VAR(name), x, y), function (matched) {
        return APP(lambda(matched.name, t(matched.y)), t(matched.x));
      },
      JOIN(x, y), function (matched) {
        return APP(APP(J, t(matched.x)),  t(matched.y));
      },
      RAND(x, y), function (matched) {
        return APP(APP(R, t(matched.x)),  t(matched.y));
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
    var xy = APP(x, y);  // just something that is not a variable
    var examples = [
      [TOP, TOP],
      [BOT, BOT],
      [I, LAMBDA(a, a)],
      [K, LAMBDA(a, LAMBDA(b, a))],
      [APP(K, x), LAMBDA(a, x)],
      [B, LAMBDA(a, LAMBDA(b, LAMBDA(c, APP(a, APP(b, c)))))],
      [APP(B, x), LAMBDA(a, LAMBDA(b, APP(x, APP(a, b))))],
      [APP(APP(B, x), y), LAMBDA(a, APP(x, APP(y, a)))],
      [C, LAMBDA(a, LAMBDA(b, LAMBDA(c, APP(APP(a, c), b))))],
      [APP(C, x), LAMBDA(a, LAMBDA(b, APP(APP(x, b), a)))],
      [APP(APP(C, x), y), LAMBDA(a, APP(APP(x, a), y))],
      [W, LAMBDA(a, LAMBDA(b, APP(APP(a, b), b)))],
      [APP(W, x), LAMBDA(a, APP(APP(x, a), a))],
      [APP(APP(W, x), xy), LET(a, xy, APP(APP(x, a), a))],
      [S, LAMBDA(a, LAMBDA(b, LAMBDA(c, APP(APP(a, c), APP(b, c)))))],
      [APP(S, x), LAMBDA(a, LAMBDA(b, APP(APP(x, b), APP(a, b))))],
      [APP(APP(S, x), y), LAMBDA(a, APP(APP(x, a), APP(y, a)))],
      [APP(APP(APP(S, x), y), xy), LET(a, xy, APP(APP(x, a), APP(y, a)))],
      [J, LAMBDA(a, LAMBDA(b, JOIN(a, b)))],
      [APP(J, x), LAMBDA(a, JOIN(x, a))],
      [APP(APP(J, x), y), JOIN(x, y)],
      [APP(APP(APP(J, x), y), I), APP(JOIN(x, y), LAMBDA(a, a))],
      [R, LAMBDA(a, LAMBDA(b, RAND(a, b)))],
      [APP(R, x), LAMBDA(a, RAND(x, a))],
      [APP(APP(R, x), y), RAND(x, y)],
      [APP(APP(APP(R, x), y), I), APP(RAND(x, y), LAMBDA(a, a))],
      [QUOTE(I), QUOTE(LAMBDA(a, a))],
      [APP(QUOTE(x), I), APP(QUOTE(x), LAMBDA(a, a))],
      [VAR(x), VAR(x)],
      [APP(VAR(x), I), APP(VAR(x), LAMBDA(a, a))],
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
    var xy = APP(x, y);  // just something that is not a variable
    var examples = [
      [APP(APP(W, x), y), APP(APP(x, y), y)],
      [APP(APP(APP(W, x), y), I), APP(APP(APP(x, y), y), LAMBDA(a, a))],
      [APP(APP(APP(S, x), y), z), APP(APP(x, z), APP(y, z))],
      [APP(APP(APP(APP(S, x), y), z), I),
       APP(APP(APP(x, z), APP(y, z)), LAMBDA(a, a))]
    ];
    assert.forward(toLambda, examples);
  });

  test('compiler.fromLambda', function () {
    // toLamda would fail these because input is not simple
    var a = VAR('a');
    var x = VAR('x');
    var examples = [
      [APP(LAMBDA(a, a), x), APP(I, x)]
    ];
    assert.forward(fromLambda, examples);
  });

  return compiler;
});
