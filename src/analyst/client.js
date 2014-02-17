'use strict';

var assert = require('assert');
var _ = require('underscore');
var zmq = require('zmq');
var protobuf = require('protobufjs').loadProtoFile('messages.proto');

exports.connect = function (address) {
  'use strict';

  address = (
    address ||
    process.env.POMAGMA_ANALYST_ADDRESS ||
    'tcp://localhost:34936'
  );

  var socket = zmq.socket('req');
  socket.connect(address);
  console.log('connected to pomagma analyst at ' + address);

  var ping = function (done) {
    done();
  };

  var validateCorpus = function (lines, done) {
    var result = _.map(lines, function(){
      return {
        'is_bot': null,
        'is_top': null,
        'pending': false
      };
    });
    done(result);
  };

  return {
    address: function(){
      return address;
    },
    ping: ping,
    validateCorpus: validateCorpus,
    close: function() {
      socket.close();
      console.log('disconnected from pomagma analyst');
    }
  };
};
