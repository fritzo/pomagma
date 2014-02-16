'use strict';

var assert = require('assert');
var _ = require('underscore');
var zmq = require('zmq');
var protobufjs = require('protobufjs');

exports.validateCorpus = function (lines) {
  return _.map(lines, function () {
    return {
      'is_bot': null,
      'is_top': null,
      'pending': false
    };
  });
};
