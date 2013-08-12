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
      'LETREC VAR i LAMBDA VAR x VAR x APP VAR i VAR i'
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

  ast.cursor.remove = function (cursor) {
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

  ast.cursor.insertBelow = function (cursor, above, pos) {
    var below = above.below[pos];
    above.below[pos] = cursor;
    cursor.above = above;
    below.above = cursor;
    cursor.below[0] = below;
  };

  ast.cursor.insertAbove = function (cursor, below) {
    cursor.below[0] = below;
    var above = below.above;
    below.above = cursor;
    cursor.above = above;
    if (above !== null) {
      var pos = above.below.indexOf(below);
      above.below[pos] = cursor;
    }
  };

  ast.cursor.replaceBelow = (function(){
    var findCursor = function (term) {
      if (term.name === 'CURSOR') {
        return term;
      } else {
        for (var i = 0; i < term.below.length; ++i) {
          var cursor = findCursor(term.below[i]);
          if (cursor !== undefined) {
            return cursor;
          }
        }
      }
    };
    return function (oldCursor, newTerm) {
      var newCursor = findCursor(newTerm);
      if (newCursor === undefined) {
        newCursor = ast.cursor.create();
        ast.cursor.insertAbove(newCursor, newTerm);
        newTerm = newCursor;
      }
      var above = oldCursor.above;
      assert(above !== null, 'tried to replace with cursor at root');
      var pos = ast.cursor.remove(oldCursor);
      above.below[pos] = newTerm;
      newTerm.above = above;
      return newCursor;
    };
  })();

  ast.cursor.tryMove = (function(){

    var traverseDownLeft = function (node) {
      while (node.below.length) {
        node = node.below[0];
      }
      return node;
    };

    var traverseDownRight = function (node) {
      while (node.below.length) {
        node = node.below[node.below.length - 1];
      }
      return node;
    };

    var traverseLeftDown = function (node) {
      var above = node.above;
      while (above !== null) {
        var pos = _.indexOf(above.below, node);
        assert(pos >= 0, 'node not found in node.above.below');
        if (pos > 0) {
          return traverseDownRight(above.below[pos - 1]);
        }
        node = above;
        above = node.above;
      }
      return traverseDownRight(node);
    };

    var traverseRightDown = function (node) {
      var above = node.above;
      while (above !== null) {
        var pos = _.indexOf(above.below, node);
        assert(pos >= 0, 'node not found in node.above.below');
        if (pos < above.below.length - 1) {
          return traverseDownLeft(above.below[pos + 1]);
        }
        node = above;
        above = node.above;
      }
      return traverseDownLeft(node);
    };

    var insertBelowLeft = function (cursor, start) {
      while (start.above !== null) {
        start = start.above;
      }
    };

    var tryMoveLeft = function (cursor) {
      var node = cursor.below[0];
      ast.cursor.remove(cursor);
      var next = traverseLeftDown(node);
      ast.cursor.insertAbove(cursor, next);
      return true;
    };

    var tryMoveRight = function (cursor) {
      var node = cursor.below[0];
      ast.cursor.remove(cursor);
      var next = traverseRightDown(node);
      ast.cursor.insertAbove(cursor, next);
      return true;
    };

    var tryMoveUp = function (cursor) {
      if (cursor.above !== null) {
        var pivot = cursor.above;
        ast.cursor.remove(cursor);
        ast.cursor.insertAbove(cursor, pivot);
        return true;
      } else {
        return false;
      }
    };

    var tryMoveDown = function (cursor) {
      var pivot = cursor.below[0];
      if (pivot.below.length > 0) {
        ast.cursor.remove(cursor);
        ast.cursor.insertBelow(cursor, pivot, 0);
        return true;
      } else {
        return false;
      }
    };

    return function (cursor, direction) {
      switch (direction) {
        case 'U': return tryMoveUp(cursor);
        case 'L': return tryMoveLeft(cursor);
        case 'D': return tryMoveDown(cursor);
        case 'R': return tryMoveRight(cursor);
      }
    };
  })();

  //--------------------------------------------------------------------------
  // Transformations

  ast.getRoot = function (indexed) {
    while (indexed.above !== null) {
      indexed = indexed.above;
    }
    return indexed;
  };

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

  ast.getBoundAbove = function (term) {
    var result = [];
    for (var above = term; above !== null; above = above.above) {
      if (above.name === 'LAMBDA' || above.name === 'LETREC') {
        var patt = above.below[0];
        pushPatternVars(patt, result);
      }
    }
    return result;
  };

  ast.getVars = (function(){
    var getVarsBelow = function (node, vars) {
      if (node.name === 'VAR') {
        vars[node.varName] = null;
      } else {
        var below = node.below;
        for (var i = 0; i < below.length; ++i) {
          getVarsBelow(below[i], vars);
        }
      }
    };
    return function (node) {
      var vars = {};
      var root = ast.getRoot(node);
      getVarsBelow(root, vars);
      return vars;
    };
  })();

  ast.getFresh = function (node) {
    var avoid = ast.getVars(node);
    for (var i = 0; true; ++i) {
      var name = compiler.enumerateFresh(i);
      if (!_.has(avoid, name)) {
        return name;
      }
    }
  };

  return ast;
});
