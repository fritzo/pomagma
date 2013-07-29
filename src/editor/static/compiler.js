/**
 * Syntactic Transforms.
 *
 * appTree is the lingua franca.
 */

define(['log', 'test', 'pattern', 'symbols'],
function(log,   test,   pattern,   symbols)
{
  //--------------------------------------------------------------------------
  // Parse

  var parse = (function(){

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

  var parseLine = function (line) {
    var name = line.name;
    var body = parse(line.code);
    if (name !== null) {
      return DEFINE(VAR(name), body);
    } else {
      return ASSERT(body);
    }
  };

  //--------------------------------------------------------------------------
  // Serialize

  var print = (function(){
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

  var symbols = {};
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
    symbols[name] = symbol;
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
  var DEFINE = Symbol('DEFINE', 2);
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

  var comp = function (term) {
    for (var i = 1; i < arguments.length; ++i) {
      term = ['APP', ['APP', 'B', term], arguments[i]];
    }
    return term;
  };

  test('compiler.comp', function(){
    assert.equal(
      comp('x', 'y'),
      APP(APP('B', 'x'), 'y'));
    assert.equal(
      comp('x', 'y', 'z'),
      APP(APP('B', APP(APP('B', 'x'), 'y')), 'z'));
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

  //--------------------------------------------------------------------------
  // Conversion : appTree <-> code

  var definitions = {}
  definitions.CI = app(C, I);
  definitions.CB = app(C, B);
  definitions.U = comp(Y, comp(app(S, B), app(J, app(C, B, I)), app(C, B)));
  definitions.V = comp(definitions.U, app(J, I));
  definitions.P = comp(app(B, definitions.V), J);
  definitions.A = HOLE;  // TODO define

  //--------------------------------------------------------------------------
  // Convert : appTree <-> stack

  var toStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var tail = pattern.variable('tail');
    var t = pattern.match([
      app(x, y), function (m, tail) {
        return t(m.x, stack(m.y, tail));
      },
      x, function (m, tail) {
        return stack(m.x, tail)
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
      stack(x, y, tail), function (m) {
        return t(stack(app(m.x, m.y), m.tail));
      },
      stack(x, []), function (m) {
        return m.x;
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
  //
  // Implements affine-beta-eta reduction for lambda-let terms.
  /* TODO
  var simplifyStack = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var tail = pattern.variable('tail');

    var simplifyStack = pattern.match([
      stack(TOP, tail), function (m) {
        return stack(TOP, []);
      },
      stack(BOT, tail), function (m) {
        return stack(BOT, []);
      },
      stack(I, x, tail), function (m) {
        var step = toStack(m.x, m.tail);
        return simplifyStack(step);
      },
      stack(K, x, y, tail), function (m) {
        var step = toStack(m.x, m.tail);
        return simplifyStack(step);
      },
      stack(B, x, y, z, tail), function (m) {
        var yz = app(m.y, m.z);
        var step = toStack(m.x, yz, m.tail);
        return simplifyStack(step);
      },
      stack(C, x, y, z, tail), function (m) {
        var step = toStack(m.x, m.z, m.y, m.tail);
        return simplifyStack(step);
      },
      stack(W, x, VAR(name), tail), function (m) {
        var y = VAR(m.name);
        var step = toStack(m.x, y, y, m.tail);
        return simplifyStack(step);
      },
      stack(S, x, y, VAR(name), tail), function (m) {
        var z = VAR(m.name);
        var step = toStack(m.x, z, app(m.y, yz), m.tail);
        return simplifyStack(step);
      },
      stack(J, TOP, tail), function (m) {
        return stack(TOP, []);
      },
      stack(J, x, TOP, tail), function (m) {
        return stack(TOP, []);
      },
      stack(J, BOT, tail), function (m) {
        var step = stack(I, m.tail);
        return simplifyStack(step);
      },
      stack(J, x, BOT, tail), function (m) {
        var step = stack(m.x, m.tail);
        return simplifyStack(step);
      },
      stack(J, x, y, VAR(name), tail), function (m) {
        var z = VAR(m.name);
        var step = stack(J, app(m.x, z), app(m.y, z), m.tail);
        return simplifyStack(step);
      },
      stack(R, x, y, VAR(name), tail), function (m) {
        var z = VAR(m.name);
        var step = stack(R, app(m.x, z), app(m.y, z), m.tail);
        return simplifyStack(step);
      },
      stack(x, tail), function (m) {
        var tail = simplifyArgs(m.tail);
        return stack(m.x, tail);
      }
    ]);

    var simplifyArgs = pattern.match([
      stack(x, y), function (m) {
        var rx = simplify(m.x);
        var ry = simplifyArgs(m.y);
        return stack(rx, ry);
      },
      [], function () {
        return [];
      }
    ]);

    return simplifyStack;
  })();

  var simplify = function (appTree) {
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
    var tail = HOLE;
    var examples = [
      [app(BOT, x, tail), BOT],
      [app(TOP, x, tail), TOP],
      [app(K, x, y, tail), app(x, tail)],
      [app(B, x, y, z, tail), app(x, app(y, z), tail)],
      [app(C, x, y, z), app(x, z, y)],
      [app(B, x, app(K, y), z, tail), app(x, y, tail)],
      [app(B, app(I, x), app(K, y, z)), app(B, x, y)],
      [app(J, TOP, tail), TOP],
      [app(J, x, TOP, tail), TOP],
      [app(J, BOT, tail), tail],
      [app(J, x, BOT, tail), app(x, tail)],
      // FIXME why don't these work?
      //[app(J, x, y, z, tail), app(J, app(x, z), app(y, z), tail)],
      //[app(R, x, y, z, tail), app(R, app(x, z), app(y, z), tail)],
      [HOLE, HOLE]
    ];
    assert.forward(simplify, examples);
  });
  */

  //--------------------------------------------------------------------------
  // Convert : simple appTree -> lambda

  var lambdaSymbols = (function(){
    var subset = [
      'HOLE', 'TOP', 'BOT',
      //'I', 'K', 'B', 'C', 'W', 'S', 'Y', 'U', 'V', 'P', 'A', 'J', 'R',
      'APP', 'LAMBDA', 'LET', 'JOIN', 'RAND',
      'QUOTE', 'QLESS', 'QNLESS', 'QEQUAL', 'LESS', 'NLESS', 'EQUAL',
      'ASSERT', 'DEFINE', 'CURSOR',
    ];
    var lambdaSymbols = {};
    subset.forEach(function(name){
      lambdaSymbols[name] = symbols[name];
    });
    return lambdaSymbols;
  })();

  var decompile = (function(){

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
    var head = pattern.variable('head');
    var tail = pattern.variable('tail');
    var name = pattern.variable('name');
    var array = pattern.variable('array', _.isArray);
    var atom = pattern.variable('atom', function (struct) {
      return _.isString(struct) && _.has(definitions, struct);
    });

    var decompileStack = pattern.match([
      stack(COMP(x, y), tail), function (m) {
        return decompileStack(stack(B, m.x, m.y, m.tail));
      },
      stack(HOLE, tail), function (m) {
        return fromStack(stack(HOLE, decompileTail(m.tail)));
      },
      stack(TOP, tail), function () {
        return TOP;
      },
      stack(BOT, tail), function () {
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
      stack(K, x, []), function (m) {
        var y = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, tx);
      },
      stack(C, I, []), function (m) {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, app(y, x)));
      },
      stack(C, I, x, []), function (m) {
        var y = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, app(y, tx));
      },
      // TODO simplify B, C, W, S cases with a popFresh(cb) function
      // Johann implements this by keeping (binder-stack, app-stack)
      // and pushing binders onto the stack when creating fresh
      // see johann/src/expressions.C class Decompile
      stack(B, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, app(y, z)))));
      },
      stack(B, x, []), function (m) {
        var y = fresh();
        var z = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, LAMBDA(z, app(tx, app(y, z))));
      },
      stack(B, x, y, []), function (m) {
        var z = fresh();
        var tx = decompile(m.x);
        var ty = decompile(m.y);
        return LAMBDA(z, app(tx, app(ty, z)));
      },
      stack(C, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, z, y))));
      },
      stack(C, x, []), function (m) {
        var y = fresh();
        var z = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, LAMBDA(z, app(tx, z, y)));
      },
      stack(C, x, y, []), function (m) {
        var z = fresh();
        var tx = decompile(m.x);
        var ty = decompile(m.y);
        return LAMBDA(z, app(tx, z, ty));
      },
      stack(W, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, app(x, y, y)));
      },
      stack(W, x, []), function (m) {
        var y = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, app(tx, y, y));
      },
      stack(W, x, VAR(name), tail), function (m) {
        var y = VAR(m.name);
        var head = decompile(app(m.x, y, y));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(W, x, y, tail), function (m) {
        var y = fresh();
        var ty = decompile(m.y);
        var head = LET(y, ty, decompile(app(m.x, y, y)));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, []), function () {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LAMBDA(y, LAMBDA(z, app(x, z, app(y, z)))));
      },
      stack(S, x, []), function (m) {
        var y = fresh();
        var z = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, LAMBDA(z, app(tx, z, app(y, z))));
      },
      stack(S, x, y, []), function (m) {
        var z = fresh();
        var tx = decompile(m.x);
        var ty = decompile(m.y);
        return LAMBDA(z, app(tx, z, app(ty, z)));
      },
      stack(S, x, y, VAR(name), tail), function (m) {
        var z = VAR(m.name);
        var head = decompile(app(m.x, z, app(m.y, z)));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(S, x, y, z, tail), function (m) {
        var z = fresh();
        var tz = decompile(m.z);
        var xz = app(m.x, z);
        var yz = app(m.y, z);
        var head = LET(z, tz, decompile(app(xz, yz)));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(Y, []), function (m) {
        var x = fresh();
        var y = fresh();
        var z = fresh();
        return LAMBDA(x, LET(y, LAMBDA(z, app(x, app(y, z))), y));
      },
      stack(Y, x, tail), function (m) {
        var y = fresh();
        var z = fresh();
        var tx = decompile(m.x);
        var head = LET(y, LAMBDA(z, app(tx, app(y, z))), y);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(J, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, JOIN(x, y)));
      },
      stack(J, x, []), function (m) {
        var y = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, JOIN(tx, y));
      },
      stack(J, x, y, tail), function (m) {
        var tx = decompile(m.x);
        var ty = decompile(m.y);
        var head = JOIN(tx, ty);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(R, []), function () {
        var x = fresh();
        var y = fresh();
        return LAMBDA(x, LAMBDA(y, RAND(x, y)));
      },
      stack(R, x, []), function (m) {
        var y = fresh();
        var tx = decompile(m.x);
        return LAMBDA(y, RAND(tx, y));
      },
      stack(R, x, y, tail), function (m) {
        var tx = decompile(m.x);
        var ty = decompile(m.y);
        var head = RAND(tx, ty);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      // TODO reimplement via ensureQuoted
      stack(QLESS, []), function (m) {
        var x = fresh();
        var y = fresh();
        return LAMBDA(QUOTE(x), LAMBDA(QUOTE(y), LESS(x, y)));
      },
      stack(QLESS, QUOTE(x), []), function (m) {
        var y = fresh();
        return LAMBDA(QUOTE(y), LESS(m.x, y));
      },
      stack(QLESS, x, []), function (m) {
        var x = fresh();
        var y = fresh();
        return LET(QUOTE(x), m.x, LAMBDA(QUOTE(y), LESS(x, y)));
      },
      // ... other cases omitted: (QUOTE(x), y); (x, QUOTE(y))
      stack(QLESS, QUOTE(x), QUOTE(y), tail), function (m) {
        var head = LESS(m.x, m.y);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(QLESS, x, y, tail), function (m) {
        var x = fresh();
        var y = fresh();
        var head = LET(QUOTE(x), m.x, LET(QUOTE(y), m.y, LESS(x, y)));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(QNLESS, QUOTE(x), QUOTE(y), tail), function (m) {
        var head = NLESS(m.x, m.y);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(QEQUAL, QUOTE(x), QUOTE(y), tail), function (m) {
        var head = EQUAL(m.x, m.y);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(VAR(name), tail), function (m) {
        var head = VAR(m.name);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(atom, tail), function (m) {
        var head = definitions[m.atom];
        return decompileStack(toStack(head, m.tail));
      },
      stack(array, tail), function (m) {
        var head = m.array;
        assert(_.isString(head[0]));
        head = [].concat(head);
        for (var i = 1; i < head.length; ++i) {
          head[i] = decompile(head[i]);
        }
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      }
    ]);

    var decompileTail = pattern.match([
      [], function () {
        return [];
      },
      stack(x, y), function (m) {
        var tx = decompile(m.x);
        var ty = decompileTail(m.y);
        return stack(tx, ty);
      }
    ]);

    var decompile = function (code) {
      return decompileStack(toStack(code));
    };

    return function (code) {
      fresh.reset();
      return decompile(code);
    }
  })();

  //--------------------------------------------------------------------------
  // Abstract : varName -> simple appTree -> simple appTree

  var tryAbstract = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var name = pattern.variable('name');
    var notFound = {};

    var t = pattern.match([
      VAR(name), function (m, varName) {
        if (m.name !== varName) {
          return notFound;
        } else {
          return I;
        }
      },
      APP(x, VAR(name)), function (m, varName) {
        var tx = t(m.x, varName);
        if (tx === notFound) {
          if (m.name !== varName) {
            return notFound;
          } else {
            return m.x;
          }
        } else {
          if (m.name !== varName) {
            return app(C, tx, VAR(m.name));
          } else {
            return app(W, tx);
          }
        }
      },
      APP(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound) {
          if (ty === notFound) {
            return notFound;
          } else {
            return app(B, m.x, ty);
          }
        } else {
          if (ty === notFound) {
            return app(C, tx, m.y);
          } else {
            return app(S, tx, ty);
          }
        }
      },
      COMP(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        TODO('adapt from johann/src/expressions.C Comp::abstract');
      },
      JOIN(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound) {
          if (ty === notFound) {
            return notFound;
          } else {
            // this hack will be obsoleted by simplifyLambda
            if (ty === I) {                   // HACK
              return app(J, m.x);             // HACK
            } else {                          // HACK
              return comp(app(J, m.x), ty);
            }                                 // HACK
          }
        } else {
          if (ty === notFound) {
            return comp(app(J, m.y), tx);
          } else {
            return JOIN(tx, ty);
          }
        }
      },
      RAND(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound) {
          if (ty === notFound) {
            return notFound;
          } else {
            return comp(app(R, m.x), ty);
          }
        } else {
          if (ty === notFound) {
            return comp(app(R, m.y), tx);
          } else {
            return RAND(tx, ty);
          }
        }
      },
      QUOTE(x), function (m, varName) {
        var tx = t(m.x, varName);
        if (tx === notFound) {
          return notFound;
        } else {
          TODO('implement quoted tryAbstraction');
        }
      },
      LESS(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound && ty === notFound) {
          return notFound;
        } else {
          TODO('implement quoted tryAbstraction');
        }
      },
      NLESS(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound && ty === notFound) {
          return notFound;
        } else {
          TODO('implement quoted tryAbstraction');
        }
      },
      EQUAL(x, y), function (m, varName) {
        var tx = t(m.x, varName);
        var ty = t(m.y, varName);
        if (tx === notFound && ty === notFound) {
          return notFound;
        } else {
          TODO('implement quoted tryAbstraction');
        }
      },
      x, function () {
        return notFound;
      }
    ]);

    t.notFound = notFound;

    return t;
  })();

  var compileLambda = function (varName, body) {
    var result = tryAbstract(body, varName);
    if (result === tryAbstract.notFound) {
      return app(K, body);
    } else {
      return result;
    }
  };

  test('compiler.compileLambda', function () {
    var a = VAR('a');
    var x = VAR('x');
    var y = VAR('y');
    var lambdaA = _.partial(compileLambda, 'a');
    var examples = [
      [a, I],
      [app(x, a), x],
      [app(x, a, a), app(W, x)],
      [app(y, app(x, a)), app(B, y, x)],
      [app(x, a, y), app(C, x, y)],
      [app(x, a, app(x, a)), app(S, x, x)],
      [x, app(K, x)]
    ];
    assert.forward(lambdaA, examples);
  });

  var compileLet = function (varName, def, body) {
    var bodyResult = tryAbstract(body, varName);
    if (bodyResult === tryAbstract.notFound) {
      return body;
    } else {
      var defResult = tryAbstract(def, varName);
      if (defResult === tryAbstract.notFound) {
        return app(bodyResult, def);
      } else {
        return app(bodyResult, app(Y, defResult));
      }
    }
  };

  test('compiler.compileLet', function () {
    var a = VAR('a');
    var x = VAR('x');
    var y = VAR('y');
    var letrecA = function (pair) {
      var def = pair[0];
      var body = pair[1];
      return compileLet('a', def, body);
    };
    var examples = [
      [['bomb', x], x],
      [[I, app(x, a)], app(x, I)],
      [[a, app(x, a)], app(x, app(Y, I))],
      [[app(y, a), app(x, a)], app(x, app(Y, y))]
    ];
    assert.forward(letrecA, examples);
  });

  var compile = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var name = pattern.variable('name');

    var t = pattern.match([
      VAR(name), function (m) {
        return VAR(m.name);
      },
      LAMBDA(VAR(name), x), function (m) {
        return compileLambda(m.name, t(m.x));
      },
      LET(VAR(name), x, y), function (m) {
        return compileLet(m.name, t(m.x), t(m.y));
      },
      x, function (m) {
        var x = m.x;
        if (_.isString(x)) {
          return x;
        } else {
          assert(_.isArray(x), x);
          var result = [x[0]];
          for (var i = 1; i < x.length; ++i) {
            result.push(t(x[i]));
          }
          return result;
        }
      }
    ]);

    return t;
  })();

  test('compiler.decompile, compiler.compile', function(){
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
      [app(C, I), LAMBDA(a, LAMBDA(b, app(b, a)))],
      [app(C, I, x), LAMBDA(a, app(a, x))],
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
      // TODO add these after simplifyLambda works
      //[app(J, x, y), JOIN(x, y)],
      //[app(J, x, y, I), app(JOIN(x, y), LAMBDA(a, a))],
      //[R, LAMBDA(a, LAMBDA(b, RAND(a, b)))],
      //[app(R, x), LAMBDA(a, RAND(x, a))],
      //[app(R, x, y), RAND(x, y)],
      //[app(R, x, y, I), app(RAND(x, y), LAMBDA(a, a))],
      [QUOTE(I), QUOTE(LAMBDA(a, a))],
      [app(QUOTE(x), I), app(QUOTE(x), LAMBDA(a, a))],
      [LESS(x, y), LESS(x, y)],
      [NLESS(x, y), NLESS(x, y)],
      [EQUAL(x, y), EQUAL(x, y)],
      [VAR(x), VAR(x)],
      [app(VAR(x), I), app(VAR(x), LAMBDA(a, a))],
      [HOLE, HOLE]
    ];
    assert.forward(decompile, examples);
    assert.backward(compile, examples);
  });

  test('compiler.decompile', function(){
    // compile would fail these because they involve pattern matching
    var a = VAR('a');
    var b = VAR('b');
    var c = VAR('c');
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var xy = app(x, y);  // just something that is not a variable
    var examples = [
      [app(W, x, y), app(x, y, y)],
      [app(W, x, y, I), app(x, y, y, LAMBDA(a, a))],
      [app(S, x, y, z), app(x, z, app(y, z))],
      [app(S, x, y, z, I), app(x, z, app(y, z), LAMBDA(a, a))],
      [Y, LAMBDA(a, LET(b, LAMBDA(c, app(a, app(b, c))), b))],
      [app(QLESS, QUOTE(x), QUOTE(y)), LESS(x, y)],
      [app(QNLESS, QUOTE(x), QUOTE(y)), NLESS(x, y)],
      [app(QEQUAL, QUOTE(x), QUOTE(y)), EQUAL(x, y)],
      // TODO move this back above
      [app(J, x, y), JOIN(x, y)],
      [app(J, x, y, I), app(JOIN(x, y), LAMBDA(a, a))],
      [HOLE, HOLE]
    ];
    assert.forward(decompile, examples);
  });

  test('compiler.compile', function () {
    // decompile would fail these because input is not simple
    var a = VAR('a');
    var x = VAR('x');
    var examples = [
      [app(LAMBDA(a, a), x), app(I, x)],
      [HOLE, HOLE]
    ];
    assert.forward(compile, examples);
  });

  //--------------------------------------------------------------------------
  // Render : lambda -> html
  //
  // see http://www.fileformat.info/info/unicode/category/Sm/list.htm

  var render = (function(){
    var newline = '\n                                                        ';
    var indent = function (i) {
      return newline.slice(0, 1 + 2 * i);
    };
    var span = function (className, text) {
      return '<span class=' + className + '>' + text + '</span>';
    };

    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var name = pattern.variable('name');

    var renderPatt = pattern.match([
      VAR(name), function (m) {
        return span('variable', m.name);
      },
      QUOTE(x), function (m) {
        return '{' + renderPatt(m.x) + '}';
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderPatt(m.x, i));
      }
    ]);

    var renderAtom = pattern.match([
      HOLE, function () {
        return '?';
        //return '&#9723;'; // empty square
        //return '&#9724;'; // filled square
      },
      TOP, function () {
        return '&#8868'; // looks like T
      },
      BOT, function () {
        return '_';
        //return '&#8869'; // looks like _|_
      },
      VAR(name), function (m) {
        return span('variable', m.name);
      },
      QUOTE(x), function (m, i) {
        return '{' + renderBlock(m.x, i) + '}';
      },
      LESS(x, y), function (m, i) {
        return '{' +
          renderJoin(m.x, i) + ' &#8849; ' + renderJoin(m.y, i) +
        '}';
      },
      NLESS(x, y), function (m, i) {
        return '{' +
          renderJoin(m.x, i) + ' &#8930; ' + renderJoin(m.y, i) +
        '}';
      },
      EQUAL(x, y), function (m, i) {
        //return '{' + renderJoin(m.x) + ' &#8801; ' + renderJoin(m.y) + '}';
        return '{' + renderJoin(m.x, i) + ' = ' + renderJoin(m.y, i) + '}';
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderAtom(m.x, i));
      },
      x, function (m, i, failed) {
        if (failed) {
          log('failed to render: ' + JSON.stringify(m.x));
          return span('error', 'compiler.render error: ' + m.x);
        }
        return '(' + renderInline(m.x, i, true) + ')';
      }
    ]);

    var renderApp = pattern.match([
      APP(x, y), function (m, i) {
        return renderApp(m.x, i) + ' ' + renderAtom(m.y, i);
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderApp(m.x, i));
      },
      x, function (m, i, failed) {
        return renderAtom(m.x, i, failed);
      }
    ]);

    var renderJoin = pattern.match([
      JOIN(x, y), function (m, i) {
        return renderJoin(m.x, i) + ' | ' + renderJoin(m.y, i);
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderJoin(m.x, i));
      },
      x, function (m, i, failed) {
        return renderApp(m.x, i, failed);
      }
    ]);

    var renderInline = pattern.match([
      LAMBDA(x, y), function (m, i) {
        return '&lambda;' + renderPatt(m.x) + '. ' + renderInline(m.y, i);
      },
      LET(x, y, z), function (m, i) {
        return (
          indent(i) + renderPatt(m.x) + ' = ' + renderJoin(m.y, i + 1) + '.' +
          indent(i) + renderBlock(m.z, i)
        );
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderInline(m.x, i));
      },
      x, function (m, i, failed) {
        return renderJoin(m.x, i, failed);
      }
    ]);

    var renderBlock = pattern.match([
      LET(x, y, z), function (m, i) {
        return (
          renderPatt(m.x) + ' = ' + renderJoin(m.y, i + 1) + '.' +
          indent(i) + renderBlock(m.z, i)
        );
      },
      CURSOR(x), function (m, i) {
        return span('cursor', renderBlock(m.x, i));
      },
      x, function (m, i) {
        return renderInline(m.x, i);
      }
    ]);

    var render = pattern.match([
      DEFINE(x, y), function (m, i) {
        return span('keyword', 'define') + ' ' + renderAtom(m.x) + ' = ' +
          renderJoin(m.y, i + 1) + '.';
      },
      ASSERT(x), function (m, i) {
        return span('keyword', 'assert') + ' ' + renderJoin(m.x, i + 1) + '.';
      },
      CURSOR(x), function (m, i) {
        return span('cursor', render(m.x, i));
      },
      x, function (m, i) {
        return renderBlock(m.x, i);
      }
    ]);

    return function (expr) {
      var indent = 0;
      return render(expr, indent);
    };
  })();

  return {
    symbols: lambdaSymbols,
    load: function (string) {
      var code = parse(string);
      var lambda = decompile(code);
      //lambda = simplify(lambda);  // TODO
      return lambda;
    },
    loadLine: function (line) {
      var code = parseLine(line);
      var lambda = decompile(code);
      //lambda = simplify(lambda);  // TODO
      return lambda;
    },
    dump: function (lambda) {
      var code = compile(lambda);
      return print(code);
    },
    print: print,
    render: render
  };
});
