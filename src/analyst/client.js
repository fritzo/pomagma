'use strict';

var assert = require('assert');
var path = require('path');
var _ = require('underscore');
var zmq = require('zmq');
var protobuf = require('protobufjs');

var builder = protobuf.loadProtoFile('messages.proto');

exports.connect = function (address) {
  'use strict';

  address = (
    address ||
    process.env.POMAGMA_ANALYST_ADDRESS ||
    'tcp://localhost:34936'
  );

  var socket = zmq.socket('req');
  socket.connect(address);
  console.log('Connected to pomagma analyst at ' + address);

  var validateCorpus = function (lines) {
    return _.map(lines, function () {
      return {
        'is_bot': null,
        'is_top': null,
        'pending': false
      };
    });
  };

  return {
    validateCorpus: validateCorpus
  };
};
