define(['log', 'test'],
function(log,   test)
{
  // assumptions:
  // - cache is unbounded
  // - function takes a single stringy argument
  var memoize = function (fun) {
    var cache = {};
    return function (arg) {
      assert(arguments.length === 1,
        'memoized arguments.length =' + arguments.length);
      if (_.has(cache, arg)) {
        return cache[arg];
      } else {
        log('memoizing ' + arg);
        return cache[arg] = fun(arg);
      }
    };
  };

  test('memoize', function(){
    var count = 0
    var id = memoize(function (arg) {
      count += 1;
      return arg;
    });

    assert.equal(count, 0);
    assert.equal(id('x'), 'x');
    assert.equal(count, 1);
    assert.equal(id('x'), 'x');
    assert.equal(count, 1);
    assert.equal(id('y'), 'y');
    assert.equal(count, 2);
    assert.equal(id('y'), 'y');
    assert.equal(count, 2);
    assert.equal(id('x'), 'x');
    assert.equal(count, 2);
  });

  return memoize;
});
