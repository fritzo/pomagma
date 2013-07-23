/** 
 * abstract syntax trees with crosslinks for constant time traversal
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

  // special case: DEFINE
  loadSymbol['DEFINE'] = function (flat) {
    return {
      name: 'DEFINE',
      varName: flat[1],
      below: [flat[2]],
      above: null
    };
  };
  dumpSymbol['DEFINE'] = function (indexed) {
    return ['DEFINE', indexed.varName, indexed.below[0]];
  };

  // special case: LET
  //
  //loadSymbol['LET'] = function (flat) {
  //  return {
  //    name: 'LET',
  //    binds: flat[0],
  //    below: [flat[1]],
  //    above: null
  //  };
  //};
  //
  //dumpSymbol['LET'] = function (indexed) {
  //  return ['LET', indexed.binds, indexed.below[0]];
  //};

  test('ast.load, ast.dmup', function(){
    var examples = [
      'VAR x',
      'QUOTE APP LAMBDA CURSOR VAR x VAR x HOLE',
      'LET VAR i LAMBDA VAR x VAR x APP VAR i VAR i'
    ];
    for (var i = 0; i < examples.length; ++i) {
      var lineno = 1 + i;
      var string = examples[i];
      var flat = compiler.parse(string);
      var indexed = load(flat);
      var flat2 = dump(indexed);
      assert.equal(flat2, flat, 'Example ' + lineno);
    }
  });

  //--------------------------------------------------------------------------
  // CURSOR movement

  ast.cursor = {};

  var remove = ast.cursor.remove = function (cursor) {
    var above = cursor.above;
    cursor.below[0].above = above;
    if (above) {
      var pos = above.below.indexOf(cursor);
      above.below[pos] = cursor.below[0];
      return pos;
    }
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
    var flat = compiler.parse(string);
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
  // Pretty printing

  var KEYWORDS = (function(){
    var keywords = {
      'let': 'let',
      '=': '=',
      'in': 'in',
      'fun': 'fun'
    };
    for (var key in keywords) {
      keywords[key] = '<span class=keyword>' + keywords[key] + '</span>';
    }
    return keywords;
  })();

  var indent = function (line) {
    return '    ' + line;
  };

  ast.lines = function (indexed) {
    // TODO actually pretty print
    return [compiler.print(dump(indexed))];
  };

  /*
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
  */

  //--------------------------------------------------------------------------
  // Transformations

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
