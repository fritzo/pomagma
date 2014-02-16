'use strict';

var assert = require('assert');
var path = require('path');
var _ = require('underscore');
var zmq = require('zmq');
var protobuf = require('protobufjs');

var ADDRESS = process.env.POMAGMA_ANALYST_ADDRESS || 'tcp://localhost:34936';
var socket = zmq.socket('req');
socket.connect(ADDRESS);
console.log('connected to ' + ADDRESS);

var builder = protobuf.loadProtoFile('messages.proto');

exports.validateCorpus = function (lines) {
  return _.map(lines, function () {
    return {
      'is_bot': null,
      'is_top': null,
      'pending': false
    };
  });
};
