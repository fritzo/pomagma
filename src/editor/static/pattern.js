define(['test'],
function(test)
{
  var pattern = {};

  var isVariable = function (patt) {
    return patt.constructor.name === 'Variable';
  }

  var isPattern = function (patt) {
    return _.isArray(patt) || _.isString(patt) || isVariable(patt);
  };

  var isStructure = function (struct) {
    return _.isArray(struct) || _.isString(struct);
  };

  pattern.variable = (function(){
    /** @constructor */
    var Variable = function Variable (name) {
      this.name = name;
    };
    
    Variable.prototype.toString = function () {
      return 'Variable(' + this.name + ')';
    };

    return function (name) {
      return new Variable(name);
    };
  })();

  var dispatch = {
    'String': {
      'String' : function (handler, struct, patt, transform) {
        if (struct === patt) {
          return handler(struct, patt, transform);
        }
      },
      'Variable': function (handler, struct, patt, transform) {
        return handler(struct, patt, transform);
      }
    },
    'Array': {
      'Array': function (handler, struct, patt, transform) {
        if (struct.length == patt.length) {
          var assignments = {};
          for (var i = 0; i < struct.length; ++i) {
            var structI = struct[i];
          }
        }
      },
      'Variable': function (handler, struct, patt, transform) {
        return handler(struct, patt, transform);
      }
    }
  };

  pattern.match = function (pattHandlers) {
    return function (struct) {
      assert(isStructure(struct), 'bad structure: ' + struct);
      var dispatchPatt = dispatchStruct[struct.constructor.name];
      for (var line = 0; 2 * line < pattHandlers.length; ++line) {
        var patt = pattHandlers[2 * line][0];
        var handler = pattHandlers[2 * line + 1][1];
        assert(isPattern(patt), 'bad pattern at pos ' + line + ': ' + patt);
        assert(_.isFunction(handler), 'bad handler at line ' + line);

        var case_ = dispatchPatt[patt.constructor.name];
        if (case_ !== undefined) {
          var result = case_(handler, struct, patt, transform);
          if (result !== undefined) {
            return result;
          }
        }
      }
    };
  };

  return pattern;
});
