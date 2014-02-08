define(function(require){
  'use strict';

  var _ = require('lib/underscore');
  var assert = require('assert');
  var test = require('test');

  /**
   * @constructor
   * @param {string}
   * @param {(function(?): boolean)=}
   */
  var Variable = function Variable (name, constraint) {
    this.name = name;
    this.constraint = (constraint !== undefined) ? constraint : null;
  };
  
  Variable.prototype.toString = function () {
    return 'Variable(' + this.name + ')';
  };

  var variable = function (name, constraint) {
    return new Variable(name, constraint);
  };

  var isVariable = function (thing) {
    return !!(thing && thing.constructor === Variable);
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
        if (_.has(avoid, patt.name)) {
          return false;
        } else {
          avoid[patt.name] = null;
          return true;
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
    assert.forward(isPattern, examples);
  });

  var unify = function (patt, struct, matched) {
    if (isVariable(patt)) {
      if (patt.constraint === null || patt.constraint(struct)) {
        //matched = _.extend({}, matched);  // copy to allow backtracking
        matched[patt.name] = struct;
        return matched;
      }
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

  var match = function () {
    // check statically
    assert(arguments.length % 2 == 0, 'bad pattern,handler list');
    var lineCount = arguments.length / 2;
    var patts = [];
    var handlers = [];
    for (var line = 0; line < lineCount; ++line) {
      var patt = arguments[2 * line];
      var handler = arguments[2 * line + 1];
      assert(isPattern(patt), 'bad pattern at line ' + line + ':\n  ' + patt);
      assert(_.isFunction(handler), 'bad handler at line ' + line);
      patts.push(patt);
      handlers.push(handler);
    }
    // run optimized
    var slice = Array.prototype.slice;
    return function (struct) {
      for (var line = 0; line < lineCount; ++line) {
        var matched = unify(patts[line], struct, {});
        if (matched !== undefined) {
          var args = slice.call(arguments);
          args[0] = matched;
          var result = handlers[line].apply(null, args);
          if (result !== undefined) {
            return result;
          }
        }
      }
      throw 'Unmatched Expression:\n  ' + JSON.stringify(struct);
    };
  };

  test('pattern.match', function(){
    var x = variable('x');
    var y = variable('y');
    var z = variable('z');
    var string = variable('string', _.isString);
    var array = variable('array', _.isArray);

    var t = match(
      ['APP', 'I', x], function (match) {
        var tx = t(match.x);
        return tx;
      },
      ['APP', ['APP', 'K', x], y], function (match) {
        var tx = t(match.x);
        return tx;
      },
      ['APP', ['APP', ['APP', 'B', x], y], z], function (match) {
        var xyz = ['APP', match.x, ['APP', match.y, match.z]];
        return t(xyz);
      },
      ['APP', x, y], function (match) {
        var tx = t(match.x);
        var ty = t(match.y);
        return ['APP', tx, ty];
      },
      ['typed:', string], function (match) {
        return 'string';
      },
      ['typed:', array], function (match) {
        return 'array';
      },
      x, function (match) {
        return match.x;
      }
    );

    var examples = [
      [['APP', 'I', 'a'], 'a'],
      [['APP', ['APP', 'K', 'a'], 'b'], 'a'],
      [['typed:', 'test'], 'string'],
      [['typed:', []], 'array']
    ];
    assert.forward(t, examples);
  });

  /** @exports pattern */
  return {
    variable: variable,
    unify: function (patt, struct) {
      assert(isPattern(patt), 'bad pattern: ' + patt);
      return unify(patt, struct, {});
    },
    match: match
  };
});
