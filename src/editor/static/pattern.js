define(['log', 'test'],
function(log, test)
{
  var pattern = {};

  /** @constructor */
  var Variable = function Variable (name) {
    this.name = name;
  };
  
  Variable.prototype.toString = function () {
    return 'Variable(' + this.name + ')';
  };

  var variable = pattern.variable = function (name) {
    return new Variable(name);
  };

  var isVariable = function (thing) {
    if (thing && thing.constructor === Variable) {
      return true;
    } else {
      return false;
    }
  };

  test('pattern.isVariable', function(){
    var examples = [
      [variable('a'), true],
      ['asdf', false],
      [{}, false],
      [[], false],
      [undefined, false]
    ];
    examples.forEach(function(pair){
      var thing = pair[0];
      assert(isVariable(thing) === pair[1], 'isVariable failed on ' + thing);
    });
  });

  var isPattern = (function(){
    var isPattern = function (patt, avoid) {
      if (isVariable(patt)) {
        if (avoid[patt.name] === undefined) {
          avoid[patt.name] = null;
          return true;
        } else {
          return false;
        }
      } else if (_.isString(patt)) {
        return true;
      } else if (_.isArray(patt)) {
        for (var i = 0; i < patt.length; ++i) {
          if (!isPattern(patt[i], avoid)) {
            return false;
          }
        }
        return true;
      } else {
        return false;
      }
    };
    return function (patt) {
      return isPattern(patt, {});
    };
  })();

  test('pattern.isPattern', function(){
    var examples = [
      [variable('a'), true],
      ['asdf', true],
      [{}, false],
      [[['asdf', variable('x')], variable('y')], true],
      [[variable('x'), variable('x')], false],
      [undefined, false]
    ];
    examples.forEach(function(pair){
      var thing = pair[0];
      assert(isPattern(thing) === pair[1], 'isPattern failed on ' + thing);
    });
  });

  var unify = function (patt, struct, matched) {
    if (isVariable(patt)) {
      //matched = _.clone(matched);  // only needed when backtracking
      matched[patt.name] = struct;
      return matched;
    } else if (_.isArray(patt) && _.isArray(struct)) {
      if (patt.length === struct.length) {
        for (var i = 0; i < struct.length; ++i) {
          matched = unify(patt[i], struct[i], matched);
          if (matched === undefined) {
            return;
          }
        }
        return matched;
      }
    } else if (patt === struct) {
      return matched;
    }
  };

  pattern.unify = function (patt, struct) {
    assert(isPattern(patt), 'bad pattern: ' + patt);
    return unify(patt, struct, {});
  };

  var match = pattern.match = function (pattHandlers) {
    // check statically
    assert(pattHandlers.length % 2 == 0, 'bad pattern,handler list');
    var lineCount = pattHandlers.length / 2;
    for (var line = 0; line < lineCount; ++line) {
      var patt = pattHandlers[2 * line];
      var handler = pattHandlers[2 * line + 1];
      assert(isPattern(patt), 'bad pattern at line ' + line + ':\n  ' + patt);
      assert(_.isFunction(handler), 'bad handler at line ' + line);
    }
    // run optimized
    var slice = Array.prototype.slice;
    return function (struct) {
      for (var line = 0; line < lineCount; ++line) {
        var patt = pattHandlers[2 * line];
        var matched = unify(patt, struct, {});
        if (matched !== undefined) {
          var handler = pattHandlers[2 * line + 1];
          var args = [matched].concat(slice.call(arguments, 1));
          return handler.apply(this, args);
        }
      }
      throw 'unmatched expression:\n  ' + JSON.stringify(struct);
    };
  };

  test('pattern.match', function(){
    var x = variable('x');
    var y = variable('y');
    var z = variable('z');

    var t = pattern.match([
      ['APP', 'I', x], function (matched) {
        var tx = t(matched.x);
        return tx;
      },
      ['APP', ['APP', 'K', x], y], function (matched) {
        var tx = t(matched.x);
        return tx;
      },
      ['APP', ['APP', ['APP', 'B', x], y], z], function (matched) {
        var xyz = ['APP', matched.x, ['APP', matched.y, matched.z]];
        return t(xyz);
      },
      ['APP', x, y], function (matched) {
        var tx = t(matched.x);
        var ty = t(matched.y);
        return ['APP', tx, ty];
      },
      x, function (matched) {
        return matched.x;
      }
    ]);

    var examples = [
      [['APP', 'I', 'a'], 'a'],
      [['APP', ['APP', 'K', 'a'], 'b'], 'a']
    ];
    examples.forEach(function(pair){
      var actual = t(pair[0]);
      var expected = pair[1];
      assert.equal(actual, expected);
    });
  });

  return pattern;
});
