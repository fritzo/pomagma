/** 
 * Transforms : string <-> ugly tree <-> pretty tree
 */

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
  // Serializing

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

  test('compiler.decompile', function(){
    var a = VAR('a');
    var b = VAR('b');
    var c = VAR('c');
    var examples = [
      [I, LAMBDA(a, a)]
    ];
    examples.forEach(function(pair){
      log('DEBUG ' + JSON.stringify(pair));
      var actual = pair[1];
      var expected = decompile(pair[0]);
      assert.equal(actual, expected);
    });
  });

  return compiler;
});
