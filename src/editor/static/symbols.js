define(['test'],
function(test)
{
  var symbols = {};

  var matcher = function (re) {
    return function (token) {
      if (_.isString(token) && token.match(re)) {
        return true;
      } else {
        return false;
      }
    };
  };

  symbols.isToken = matcher(/^[^\d\W]\w*(\.[^\d\W]\w*)*$/);
  symbols.isKeyword = matcher(/^[A-Z]+$/);
  symbols.isLocal = matcher(/^[a-z][a-z0-9]*$/);
  symbols.isGlobal = matcher(/^[^\d\W]\w*(\.[^\d\W]\w*)+$/);

  test('symbols.isToken', function(){
    var examples = [
      ['()', false],
      ['', false],
      ['1', false],
      ['1a', false],
      ['1.1', false],
      ['1a', false],
      ['.', false],
      ['...', false]
    ];
    assert.forward(symbols.isToken, examples);
  });

  test('symbols.isKeyword', function(){
    var examples = [
      ['asdf', false],
      ['ASDF', true],
      ['ASDF.ASDF', false],
      ['a123', false],
      ['A123', false]
    ];
    assert.forward(symbols.isKeyword, examples);

    examples.forEach(function(pair){
      pair[1] = true;
    });
    assert.forward(symbols.isToken, examples);
  });

  test('symbols.isLocal', function(){
    var examples = [
      ['asdf', true],
      ['ASDF', false],
      ['asdf.asdf', false],
      ['a123', true],
      ['A123', false]
    ];
    assert.forward(symbols.isLocal, examples);

    examples.forEach(function(pair){
      pair[1] = true;
    });
    assert.forward(symbols.isToken, examples);
  });

  test('symbols.isGlobal', function(){
    var examples = [
      ['asdf', false],
      ['ASDF', false],
      ['mod.asdf', true],
      ['mod.mod.mod.mod.mod.asdf', true],
      ['mod.asdf123', true],
      ['MOD.ASDF', true],
    ];
    assert.forward(symbols.isGlobal, examples);

    examples.forEach(function(pair){
      pair[1] = true;
    });
    assert.forward(symbols.isToken, examples);
  });

  return symbols;
});
