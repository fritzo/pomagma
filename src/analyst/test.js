'use strict';

var fs = require('fs');
var path = require('path');
var _ = require('underscore');
var analyst = require('./client');
//var assert = require('assert');
var assert = require('chai').assert;
var describe = require('mocha').describe;
var test = require('mocha').test;
var before = require('mocha').before;
var after = require('mocha').after;

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
  client = analyst.connect();
});

after(function(){
  client.close();
});

describe('analyst', function(){

  it('has an address', function(){
    var address = client.address();
    assert.typeOf(address, 'string');
  });

  it('responds to ping', function(done){
    client.ping(done);
  });

  it('validates corpus', function(done){

    var expected = [];
    var lines = [];

    CORPUS.forEach(function(pair){
      expected.push(pair[0]);
      lines.push(pair[1]);
    });

    client.validateCorpus(lines, function(actual){
      assert.equal(actual.length, expected.length);
      _.zip(actual, expected).forEach(function(pair){
        assert.ok(equalValidity(pair[0], pair[1]));
      });
      done();
    });
  });

});
