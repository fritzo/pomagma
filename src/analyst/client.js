'use strict';

var assert = require('assert');
var _ = require('underscore');
var path = require('path');
var zmq = require('zmq');
var protobuf = require('protobufjs');

var proto = path.join(__dirname, 'messages.proto');
var messages = protobuf.loadProtoFile(proto).result.pomagma_messaging;
var Request = messages.AnalystRequest;
var Response = messages.AnalystResponse;

var WARN = function (message) {
  console.warn(message);
};

var ServerError = function (messages) {
  this.messages = messages;
};
ServerError.prototype.toString = function () {
  return 'Server Errors:\n' + this.messagess.join('\n');
};

exports.connect = function (address) {
  'use strict';
  assert(typeof address === 'string');
  var socket = zmq.socket('req');
  console.log('connecting to analyst at ' + address);
  socket.connect(address);

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
