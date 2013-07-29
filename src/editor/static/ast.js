/** 
 * abstract syntax trees with crosslinks for constant time traversal
 *
 * example ast node:
 *   {
 *     name: 'VAR',
 *     varName: flat[1],  // optional, only VAR nodes have this field
 *     below: [],
 *     above: null
 *   };
 */

define(['log', 'test', 'compiler'],
function(log,   test,   compiler)
{
  var ast = {};

  var loadSymbol = {};
  var dumpSymbol = {};

  var load = ast.load = function (flat) {
    if (_.isString(flat)) {
      return loadSymbol[flat]();
    } else {
      return loadSymbol[flat[0]](flat);
    }
  };

  var dump = ast.dump = function (indexed) {
    return dumpSymbol[indexed.name](indexed);
  };

  _.each(compiler.symbols, function(symbol, name){
    if (_.isString(symbol)) {
      loadSymbol[name] = function () {
        return {
          name: name,
          below: [],
          above: null
        };
      };
      dumpSymbol[name] = function (indexed) {
        return indexed.name;
      };
    } else {
      var arity = symbol.arity;
      loadSymbol[name] = function (flat) {
        assert(flat !== undefined);
        assert.equal(flat.length, 1 + arity, name);
        var indexed = {
          name: name,
          below: [],
          above: null
        };
        for (var i = 1; i <= arity; ++i) {
          var below = load(flat[i]);
          indexed.below.push(below);
          below.above = indexed;
        }
        return indexed;
      };
      dumpSymbol[name] = function (indexed) {
        var below = indexed.below;
        var flat = [indexed.name];
        for (var i = 0; i < arity; ++i) {
          flat.push(dump(below[i]));
        }
        return flat;
      };
    }
  });

  // special case: VAR
  loadSymbol['VAR'] = function (flat) {
    return {
      name: 'VAR',
      varName: flat[1],
      below: [],
      above: null
    };
  };
  dumpSymbol['VAR'] = function (indexed) {
    return ['VAR', indexed.varName];
  };

  test('ast.load, ast.dmup', function(){
    var examples = [
      'VAR x',
      'QUOTE APP LAMBDA CURSOR VAR x VAR x HOLE',
      'LET VAR i LAMBDA VAR x VAR x APP VAR i VAR i'
    ];
    for (var i = 0; i < examples.length; ++i) {
      var lineno = 1 + i;
      var string = examples[i];
      var flat = compiler.load(string);
      var indexed = load(flat);
      var flat2 = dump(indexed);
      assert.equal(flat2, flat, 'Example ' + lineno);
    }
  });

  //--------------------------------------------------------------------------
  // CURSOR movement

  ast.cursor = {};

  ast.cursor.create = function () {
    return {
      name: 'CURSOR',
      below: [undefined],
      above: null
    };
  };

  var remove = ast.cursor.remove = function (cursor) {
    var above = cursor.above;
    cursor.below[0].above = above;
    if (above) {
      var pos = above.below.indexOf(cursor);
      above.below[pos] = cursor.below[0];
      return pos;
    }
    cursor.below[0] = undefined;
    cursor.above = null;
  };

  var insertBelow = ast.cursor.insertBelow = function (cursor, above, pos) {
    var below = above.below[pos];
    above.below[pos] = cursor;
    cursor.above = above;
    below.above = cursor;
    cursor.below[0] = below;
  };

  var insertAbove = ast.cursor.insertAbove = function (cursor, below) {
    cursor.below[0] = below;
    var above = below.above;
    below.above = cursor;
    cursor.above = above;
    if (above !== null) {
      var pos = above.below.indexOf(below);
      above.below.below[pos] = cursor;
    }
  };

  var tryMoveDown = ast.cursor.tryMoveDown = function (cursor) {
    var pivot = cursor.below[0];
    if (pivot.below.length === 0) {
      return false;
    } else {
      ast.cursor.remove(cursor);
      insertBelow(cursor, pivot, 0);
      return true;
    }
  };

  var tryMoveUp = ast.cursor.tryMoveUp = function (cursor) {
    var pivot = cursor.above;
    if (pivot === null) {
      return false;
    } else {
      ast.cursor.remove(cursor);
      var above = pivot.above;
      if (above === null) {
        insertAbove(cursor, pivot);
      } else {
        var pos = above.below.indexOf(pivot);
        insertBelow(cursor, above, pos);
      }
      return true;
    }
  };

  var tryMoveSideways = ast.cursor.tryMoveSideways = function (cursor, direction) {
    var pivot = cursor.above;
    if ((pivot === null) || (pivot.below.length === 1)) {
      return false;
    } else {
      var pos = ast.cursor.remove(cursor);
      pos = (pos + direction + pivot.below.length) % pivot.below.length;
      insertBelow(cursor, pivot, pos);
      return true;
    }
  };

  var tryMoveLeft = ast.cursor.tryMoveLeft = function (cursor) {
    return tryMoveSideways(cursor, -1);
  };

  var tryMoveRight = ast.cursor.tryMoveRight = function (cursor) {
    return tryMoveSideways(cursor, +1);
  };

  var tryMove = ast.cursor.tryMove = function (cursor, direction) {
    switch (direction) {
      case 'U': return tryMoveUp(cursor);
      case 'L': return tryMoveLeft(cursor); // || cursor.tryMoveUp();
      case 'D': return tryMoveDown(cursor); // || cursor.tryMoveRight();
      case 'R': return tryMoveRight(cursor); // || cursor.tryMoveDown();
    }
  };

  test('ast.cursor movement', function(){
    var string = 'CURSOR LAMBDA QUOTE VAR cursor APP VAR is APP VAR a VAR test';
    var flat = compiler.load(string);
    var cursor = load(flat);
    var path =  'UDDDLRULDRDLDUUUU';
    var trace = '01100011111101110';
    for (var i = 0; i < path.length; ++i) {
      assert.equal(ast.cursor.tryMove(cursor, path[i]), !!parseInt(trace[i]));
    }
  });

  ast.getRoot = function (indexed) {
    while (indexed.above !== null) {
      indexed = indexed.above;
    }
    return indexed;
  };

  //--------------------------------------------------------------------------
  // Transformations

  var pushPatternVars = function (patt, vars) {
    switch (patt.name) {
      case 'VAR':
        vars.push(patt.varName);
        break;

      case 'QUOTE':
        pushPatternVars(patt.below[0], vars);
        break;

      default:
        break;
    }
  };

  var getBoundAbove = function (term) {
    var result = [];
    for (var above = term; above !== null; above = above.above) {
      if (above.name === 'LAMBDA' || above.name === 'LET') {
        var patt = above.below[0];
        pushPatternVars(patt, result);
      }
    }
    return result;
  };

  ast.neighborhood = (function(){
    var HOLE = compiler.symbols.HOLE;
    var TOP = compiler.symbols.TOP;
    var BOT = compiler.symbols.BOT;
    var VAR = compiler.symbols.VAR;
    var LAMBDA = compiler.symbols.LAMBDA;
    var LET = compiler.symbols.LET;
    var APP = compiler.symbols.APP;
    var JOIN = compiler.symbols.JOIN;
    var RAND = compiler.symbols.RAND;
    var QUOTE = compiler.symbols.QUOTE;

    return function (cursor) {
      var term = cursor.below[0];
      var result = [];
      var name = term.name;
      if (name === 'HOLE') {
        result.push(
          TOP,
          BOT,
          LAMBDA(HOLE, HOLE),
          LET(HOLE, HOLE, HOLE),
          APP(HOLE, HOLE),
          JOIN(HOLE, HOLE),
          RAND(HOLE, HOLE),
          QUOTE(HOLE)
        );
        var bound = getBoundAbove(term);
        bound.forEach(function(varName){
          result.push(VAR(varName));
        });
      } else {
        var dumped = dump(term);
        var fresh = HOLE;  // TODO create fresh variable
        result.push(
          LAMBDA(fresh, dumped),
          LET(fresh, dumped, HOLE),
          LET(fresh, HOLE, dumped),
          APP(dumped, HOLE),
          APP(HOLE, dumped),
          JOIN(dumped, HOLE),
          RAND(dumped, HOLE),
          QUOTE(dumped)
        );
        switch (name) {
          case 'TOP':
          case 'BOT':
            result.push(HOLE);
            break;

          default:
            break;
        }
      }
      return result;
    };
  })();

  /*
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
  */

  return ast;
});
