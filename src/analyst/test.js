'use strict';

var fs = require('fs');
var path = require('path');
var _ = require('underscore');
var pomagma = require('../index');
var assert = require('chai').assert;
var suite = require('mocha').suite;
var test = require('mocha').test;
var before = require('mocha').before;
var after = require('mocha').after;

var THEORY = process.env.THEORY || 'skj';
var DATA = path.join(pomagma.util.DATA, 'test', 'debug', 'atlas', THEORY);
var WORLD = process.env.WORLD || path.join(DATA, '0.normal.h5');
var ADDRESS = 'ipc://' + path.join(DATA, 'socket');
var OPTIONS = {
  'log_file': path.join(DATA, 'analyst_test.log'),
  'log_level': pomagma.util.LOG_LEVEL_DEBUG,
};

var json_load = function (name) {
  return JSON.parse(fs.readFileSync(path.join(__dirname, name)));
};

var SIMPLIFY_EXAMPLES = json_load('testdata/simplify_examples.json');
var VALIDATE_EXAMPLES = json_load('testdata/validate_examples.json');
var CORPUS = json_load('testdata/corpus.json');


var equalTrool = function (x, y) {
  if (x === null || y === null) {
    return true;
  } else {
    return x === y;
  }
};

var equalValidity = function (x, y) {
  return equalTrool(x.is_top, y.is_top) && equalTrool(x.is_bot, y.is_bot);
};

var client;

before(function(){
  client = pomagma.analyst.connect(ADDRESS);
  // TODO start server here; for now we start by hand externally
});

after(function(){
  client.close();
});

suite('analyst', function(){
  this.timeOut = 10000;

  test('#address', function(){
    var address = client.address();
    assert.typeOf(address, 'string');
  });

  test('#ping', function(done){
    client.ping(done);
  });

  test('#testInference', function(done){
    this.timeout(10000);
    client.testInference(function(failCount){
      assert.typeOf(failCount, 'number');
      assert.equal(failCount, 0);
      done();
    })
  });

  test('#simplify', function(done){
    var codes = _.pluck(SIMPLIFY_EXAMPLES, 0);
    var expected = _.pluck(SIMPLIFY_EXAMPLES, 1);
    client.simplify(codes, function(actual){
      assert.equal(actual.length, expected.length);
      _.zip(actual, expected).forEach(function(pair){
        assert.deepEqual(pair[0], pair[1]);
      });
      done();
    });
  });

  test('#validate', function(done){
    var expected = _.pluck(VALIDATE_EXAMPLES, 0);
    var codes = _.pluck(VALIDATE_EXAMPLES, 1);
    client.validate(codes, function(actual){
      assert.equal(actual.length, expected.length);
      _.zip(actual, expected).forEach(function(pair){
        assert.ok(equalValidity(pair[0], pair[1]));
      });
      done();
    });
  });

  test('#validateCorpus', function(done){
    var expected = _.pluck(CORPUS, 0);
    var lines = _.pluck(CORPUS, 1);
    client.validateCorpus(lines, function(actual){
      assert.equal(actual.length, expected.length);
      _.zip(actual, expected).forEach(function(pair){
        assert.ok(equalValidity(pair[0], pair[1]));
      });
      done();
    });
  });

});
