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
      'LETREC VAR i LAMBDA VAR x VAR x APP VAR i VAR i',
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
  var LETREC = Symbol('LETREC', 3);
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
  // Implements affine-beta-eta-alpha reduction for lambda-letrec terms.
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

  var normalizeAlpha = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var string = pattern.variable('string');
    var array = pattern.variable('array', _.isArray);
  
    var renamePattern = pattern.match([
      VAR(string), function (m, map) {
        assert(!_.has(map, m.string));
        var result = fresh();
        map[m.string] = result[1];
        return result;
      },
      array, function (m, map) {
        var array = [].concat(m.array);
        for (var i = 1; i < array.length; ++i) {
          array[i] = renamePattern(array[i], map);
        }
        return array;
      }
    ]);
  
    var renameTerm = pattern.match([
      VAR(string), function (m, map) {
        return VAR(map[m.string] || m.string);
      },
      LAMBDA(x, y), function (m, map) {
        map = _.extend({}, map);
        var x = renamePattern(m.x, map);
        var y = renameTerm(m.y, map);
        return LAMBDA(x, y);
      },
      LETREC(x, y, z), function (m, map) {
        map = _.extend({}, map);
        var x = renamePattern(m.x, map);
        var y = renameTerm(m.y, map);
        var z = renameTerm(m.z, map);
        return LETREC(x, y, z);
      },
      array, function (m, map) {
        var array = [].concat(m.array);
        for (var i = 1; i < array.length; ++i) {
          array[i] = renameTerm(array[i], map);
        }
        return array;
      },
      string, function (m) {
        return m.string;
      }
    ]);
  
    return function (term) {
      fresh.reset();
      return renameTerm(term, {});
    };
  })();

  test('compiler.normalizeAlpha', function(){
    var a = VAR('a');
    var b = VAR('b');
    var c = VAR('c');
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [x, x],
      [LAMBDA(x, x), LAMBDA(a, a)],
      [LETREC(x, y, x), LETREC(a, y, a)],
      [app(LAMBDA(x, x), LETREC(x, x, x)),
       app(LAMBDA(a, a), LETREC(b, b, b))],
      [app(LAMBDA(x, x), x), app(LAMBDA(a, a), x)]
    ];
    assert.forward(normalizeAlpha, examples);
  });

  var substitute = (function(){
    var string = pattern.variable('string');
    var array = pattern.variable('array', _.isArray);

    var t = pattern.match([
      VAR(string), function (m, varName, def) {
        return m.string === varName ? def : VAR(m.string);
      },
      // TODO take care with binders, or ensure variables are globally unique
      array, function (m, varName, def) {
        var array = [].concat(m.array);
        for (var i = 1; i < array.length; ++i) {
          array[i] = t(array[i], varName, def);
        }
        return array;
      },
      string, function (m) {
        return m.string;
      }
    ]);

    return function (varName, def, body) {
      return t(body, varName, def);
    };
  })();

  test('compiler.substitute', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var fun = function (args) {
      return substitute.apply(null, args);
    };
    var examples = [
      [['x', y, z], z],
      [['x', y, x], y],
      [['x', app(x, y, z), app(x, y, z)], app(app(x, y, z), y, z)]
    ];
    assert.forward(fun, examples);
  });

  var simplifyLetrec = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var name = pattern.variable('name');
    var array = pattern.variable('array', _.isArray);
    var notFound = {};

    var t = pattern.match([
      VAR(name), function (m, varName, def) {
        if (m.name !== varName) {
          return notFound;
        } else if (countOccurrences(varName, def) === 0) {
          return def;
        } else {
          return LETREC(VAR(varName), def, VAR(varName));
        }
      },
      APP(x, y), function (m, varName, def) {
        var tx = t(m.x, varName, def);
        var ty = t(m.y, varName, def);
        if (tx === notFound) {
          if (ty === notFound) {
            // unused
            return APP(m.x, m.y);
          } else {
            // narrow scope
            return APP(m.x, ty);
          }
        } else {
          if (ty === notFound) {
            // narrow scope
            return APP(tx, m.y);
          } else {
            // no-op
            return LETREC(VAR(varName), def, APP(m.x, m.y));
          }
        }
      },
      x, function (m) {
        TODO('handle ' + JSON.stringify(m.x));
      }
    ]);

    return function (varName, def, body) {
      return t(body, varName, def);
    };
  })();

  var countOccurrences = (function(){
    var string = pattern.variable('string');
    var array = pattern.variable('array', _.isArray);

    var t = pattern.match([
      VAR(string), function (m, varName) {
        return m.string === varName ? 1 : 0;
      },
      array, function (m, varName) {
        var array = m.array;
        var result = 0;
        for (var i = 1; i < array.length; ++i) {
          result += t(array[i], varName);
        }
        return result;
      },
      string, function () {
        return 0;
      }
    ]);

    return function (varName, body) {
      return t(body, varName);
    };
  })();

  test('compiler.countOccurrences', function(){
    var x = VAR('x');
    var y = VAR('y');
    var fun = function (args) {
      return countOccurrences.apply(null, args);
    };
    var examples = [
      [['x', x], 1],
      [['x', y], 0],
      [['x', I], 0],
      [['x', app(y, y)], 0],
      [['x', app(x, y)], 1],
      [['x', app(x, x, x, y, x)], 4]
    ];
    assert.forward(fun, examples);
  });

  var normalizeAffineBetaEta = (function(){
    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var name = pattern.variable('name');
    var tail = pattern.variable('tail');
    var array = pattern.variable('array', _.isArray);

    var normalizeStack = pattern.match([
      stack(TOP, tail), function (m) {
        return TOP;
      },
      stack(BOT, tail), function (m) {
        return BOT;
      },
      stack(JOIN(TOP, x), tail), function () {
        return TOP;
      },
      stack(JOIN(x, TOP), tail), function () {
        return TOP;
      },
      stack(JOIN(BOT, x), tail), function (m) {
        return normalizeStack(toStack(m.x, m.tail));
      },
      stack(JOIN(x, BOT), tail), function (m) {
        return normalizeStack(toStack(m.x, m.tail));
      },
      stack(LAMBDA(VAR(name), x), y, tail), function (m) {
        var head;
        var tail;
        switch (countOccurrences(m.name, m.y)) {
          case 0:
            return normalizeStack(toStack(m.y, m.tail));
          case 1:
            head = substitute(m.name, m.y, m.x);
            return normalizeStack(toStack(head, m.tail));
          default:
            head = LAMBDA(VAR(name), x);
            tail = normalizeTail(stack(m.y, m.tail));
            return fromStack(stack(head, tail));
        }
      },
      // TODO implement LETREC simplification
      //stack(LETREC(VAR(name), x, y), tail), function (m) {
      //  var head = normalizeLetrec(m.name. m.x, m.y);
      //  var tail = normalizeTail(tail);
      //  return fromStack(stack(head, tail));
      //},
      x, function (m) {
        return fromStack(m.x);
      }
    ]);

    var normalizeTail = pattern.match([
      [], function () {
        return [];
      },
      stack(x, y), function (m) {
        var tx = normalize(m.x);
        var ty = normalizeTail(m.y);
        return stack(tx, ty);
      }
    ]);

    var normalize = function (term) {
      return normalizeStack(toStack(term));
    };

    return normalize;
  })();

  test('compiler.normalizeAffineBetaEta', function(){
    var x = VAR('x');
    var y = VAR('y');
    var z = VAR('z');
    var examples = [
      [x, x],
      [app(LAMBDA(x, app(y, x)), z), app(y, z)],
      [LAMBDA(x, app(y, x)), y]
    ];
    assert.forward(normalizeAffineBetaEta, examples);
  });

  var simplify = function (term) {
    term = normalizeAffineBetaEta(term);
    term = normalizeAlpha(term);
    return term;
  };

  //--------------------------------------------------------------------------
  // Convert : simple appTree -> lambda

  var lambdaSymbols = (function(){
    var subset = [
      'HOLE', 'TOP', 'BOT',
      //'I', 'K', 'B', 'C', 'W', 'S', 'Y', 'U', 'V', 'P', 'A', 'J', 'R',
      'APP', 'LAMBDA', 'LETREC', 'JOIN', 'RAND',
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

    var ensureVar = function (v, handler) {
      var name = v.name;
      return function (m) {
        var tail = m.tail;
        if (tail.length === 0) {
          var v = fresh();
          m[name] = v;
          return LAMBDA(v, handler(m));
        } else {
          m[name] = decompile(tail[1]);  // FIXME calls decompile incorrectly
          m.tail = tail[2];
          return handler(m);
        }
      };
    };

    var ensure = function () {
      var pop = Array.prototype.pop;
      var handler = pop.call(arguments);
      while (arguments.length) {
        handler = ensureVar(pop.call(arguments), handler);
      }
      return function (m) {
        var head = handler(m);
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      }
    };

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
      stack(I, tail), ensure(x, function (m) {
        return m.x;
      }),
      stack(K, tail), ensure(x, y, function (m) {
        return m.x;
      }),
      stack(C, I, tail), ensure(x, y, function (m) {
        return app(m.y, m.x);
      }),
      stack(B, tail), ensure(x, y, z, function (m) {
        return app(m.x, app(m.y, m.z));
      }),
      stack(C, tail), ensure(x, y, z, function (m) {
        return app(m.x, m.z, m.y);
      }),
      // TODO get W working
      //stack(W, tail), ensure(x, y, function (m) {
      //  var x = m.x;
      //  var y = m.y;
      //  if (_.isArray(y) && y[0] === 'VAR') {
      //    return LAMBDA(x, LAMBDA(y, app(x, y, y)));
      //  } else {
      //    var z = fresh();
      //    return LETREC(z, y, app(x, z, z));
      //  }
      //}),
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
        var head = LETREC(y, ty, decompile(app(m.x, y, y)));
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
        var head = LETREC(z, tz, decompile(app(xz, yz)));
        var tail = decompileTail(m.tail);
        return fromStack(stack(head, tail));
      },
      stack(Y, tail), ensure(x, function (m) {
        var y = fresh();
        var z = fresh();
        return LETREC(y, LAMBDA(z, app(m.x, app(y, z))), y);
      }),
      stack(J, tail), ensure(x, y, function (m) {
        return JOIN(m.x, m.y);
      }),
      stack(R, tail), ensure(x, y, function (m) {
        return RAND(m.x, m.y);
      }),
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
        return LETREC(QUOTE(x), m.x, LAMBDA(QUOTE(y), LESS(x, y)));
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
        var head = LETREC(QUOTE(x), m.x, LETREC(QUOTE(y), m.y, LESS(x, y)));
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

  var compileLetrec = function (varName, def, body) {
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

  test('compiler.compileLetrec', function () {
    var a = VAR('a');
    var x = VAR('x');
    var y = VAR('y');
    var letrecA = function (pair) {
      var def = pair[0];
      var body = pair[1];
      return compileLetrec('a', def, body);
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
      LETREC(VAR(name), x, y), function (m) {
        return compileLetrec(m.name, t(m.x), t(m.y));
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
      [app(W, x, xy), LETREC(a, xy, app(x, a, a))],
      [S, LAMBDA(a, LAMBDA(b, LAMBDA(c, app(a, c, app(b, c)))))],
      [app(S, x), LAMBDA(a, LAMBDA(b, app(x, b, app(a, b))))],
      [app(S, x, y), LAMBDA(a, app(x, a, app(y, a)))],
      [app(S, x, y, xy), LETREC(a, xy, app(x, a, app(y, a)))],
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
      [Y, LAMBDA(a, LETREC(b, LAMBDA(c, app(a, app(b, c))), b))],
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
    /** @const */
    var newline = '\n                                                        '+
    '                                                                        ';
    var indent = function (i) {
      return newline.slice(0, 1 + 4 * i);
    };

    var template = function (string) {
      return function () {
        var args = arguments;
        return string.replace(/{(\d+)}/g, function(match, pos) { 
          return args[pos];
        });
      };
    };
    test('compiler.render.template', function(){
      var t = template('test {0} test {1} test {0} test');
      assert.equal(t('a', 'b'), 'test a test b test a test');
    });

    var templates = {
      HOLE: '(<span class=hole> &bullet;&bullet;&bullet; </span>)',
      TOP: '&#8868',
      BOT: '_',
      VAR: template('<span class=variable>{0}</span>'),
      APP: template('{0} {1}'),
      JOIN: template('{0} | {1}'),
      LAMBDA: template('&lambda;{0}. {1}'),
      LETREC: template('{0}let {1} = {2}.{3}{4}'),
      QUOTE: template('{{0}}'),
      LESS: template('{{0} &#8849; {1}}'),
      NLESS: template('{{0} &#8930; {1}}'),
      EQUAL: template('{{0} = {1}}'),
      DEFINE: template('<span class=keyword>define</span> {0} = {1}.'),
      ASSERT: template('<span class=keyword>assert</span> {0}.'),
      CURSOR: template('<span class=cursor>{0}</span>'),
      atom: template('({0})'),
      error: template('<span class=error>compiler.render error: {0}</span>'),
    };

    var x = pattern.variable('x');
    var y = pattern.variable('y');
    var z = pattern.variable('z');
    var name = pattern.variable('name');

    var renderPatt = pattern.match([
      VAR(name), function (m) {
        return templates.VAR(m.name);
      },
      QUOTE(x), function (m) {
        return templates.QUOTE(renderPatt(m.x));
      },
      CURSOR(x), function (m) {
        return templates.CURSOR(renderPatt(m.x));
      }
    ]);

    var renderAtom = pattern.match([
      HOLE, function () {
        return templates.HOLE;
      },
      TOP, function () {
        return templates.TOP;
      },
      BOT, function () {
        return templates.BOT;
      },
      VAR(name), function (m) {
        return templates.VAR(m.name);
      },
      QUOTE(x), function (m, i) {
        return templates.QUOTE(renderBlock(m.x, i));
      },
      LESS(x, y), function (m, i) {
        return templates.LESS(renderJoin(m.x, i), renderJoin(m.y, i));
      },
      NLESS(x, y), function (m, i) {
        return templates.NLESS(renderJoin(m.x, i), renderJoin(m.y, i));
      },
      EQUAL(x, y), function (m, i) {
        return templates.EQUAL(renderJoin(m.x, i), renderJoin(m.y, i));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(renderAtom(m.x, i));
      },
      x, function (m, i, failed) {
        if (failed) {
          log('failed to render: ' + JSON.stringify(m.x));
          return templates.error(m.x);
        } else {
          return templates.atom(renderInline(m.x, i, true));
        }
      }
    ]);

    var renderApp = pattern.match([
      APP(x, y), function (m, i) {
        return templates.APP(renderApp(m.x, i), renderAtom(m.y, i));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(renderApp(m.x, i));
      },
      x, function (m, i, failed) {
        return renderAtom(m.x, i, failed);
      }
    ]);

    var renderJoin = pattern.match([
      JOIN(x, y), function (m, i) {
        return templates.JOIN(renderJoin(m.x, i), renderJoin(m.y, i));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(renderJoin(m.x, i));
      },
      x, function (m, i, failed) {
        return renderApp(m.x, i, failed);
      }
    ]);

    var renderInline = pattern.match([
      LAMBDA(x, y), function (m, i) {
        return templates.LAMBDA(renderPatt(m.x), renderInline(m.y, i));
      },
      LETREC(x, y, z), function (m, i) {
        return templates.LETREC(
          indent(i),
          renderPatt(m.x, i),
          renderJoin(m.y, i + 1),
          indent(i),
          renderBlock(m.z, i));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(renderInline(m.x, i));
      },
      x, function (m, i, failed) {
        return renderJoin(m.x, i, failed);
      }
    ]);

    var renderBlock = pattern.match([
      LETREC(x, y, z), function (m, i) {
        return templates.LETREC(
          '',
          renderPatt(m.x, i),
          renderJoin(m.y, i + 1),
          indent(i),
          renderBlock(m.z, i));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(renderBlock(m.x, i));
      },
      x, function (m, i) {
        return renderInline(m.x, i);
      }
    ]);

    var render = pattern.match([
      DEFINE(x, y), function (m, i) {
        return templates.DEFINE(renderAtom(m.x), renderJoin(m.y, i + 1));
      },
      ASSERT(x), function (m, i) {
        return templates.ASSERT(renderJoin(m.x, i + 1));
      },
      CURSOR(x), function (m, i) {
        return templates.CURSOR(render(m.x, i));
      },
      x, function (m, i) {
        return renderBlock(m.x, i);
      }
    ]);

    return function (expr) {
      var indentLevel = 0;
      return render(expr, indentLevel);
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
