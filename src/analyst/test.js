'use strict';

var fs = require('fs');
var path = require('path');
var _ = require('underscore');
var client = require('./client').connect();
var assert = require('assert');
var suite = require('mocha').suite;
var test = require('mocha').test;

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

suite('analyst', function(){

  test('validateCorpus', function(){

    var expected = [];
    var lines = [];

    CORPUS.forEach(function(pair){
      expected.push(pair[0]);
      lines.push(pair[1]);
    });

    var actual = client.validateCorpus(lines);
    assert.equal(actual.length, expected.length);
    _.zip(actual, expected).forEach(function(pair){
      assert.ok(equalValidity(pair[0], pair[1]));
    });
  });

});
