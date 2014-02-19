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

var TROOL = [];
TROOL[Response.Trool.MAYBE] = null;
TROOL[Response.Trool.TRUE] = true;
TROOL[Response.Trool.FALSE] = false;

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

  var call = function (arg, cb) {
    socket.once('message', function(msg){
      var res = Response.decode(msg);
      console.log('DEBUG receive ' + JSON.stringify(res));
      cb(res);
    });

    var req = new Request(arg);
    var msg = req.toBuffer();
    console.log('DEBUG send ' + JSON.stringify(Request.decode(msg)));
    socket.send(msg);
  };

  var ping = function (done) {
    call({}, function(){
      done();
    });
  };

  var testInference = function (done) {
    call({test_inference: {}}, function(res){
      done(res.test_inference.fail_count.toInt());
    });
  };

  var validateCorpus = function (lines, done) {
    call({validate_corpus: {lines: lines}}, function(res){
      var results = res.validate_corpus.results;
      results.forEach(function(line){
        line.is_top = TROOL[line.is_top];
        line.is_bot = TROOL[line.is_bot];
      });
      done(results);
    });
  };

  return {
    address: function(){
      return address;
    },
    ping: ping,
    testInference: testInference,
    validateCorpus: validateCorpus,
    close: function() {
      socket.close();
      console.log('disconnected from pomagma analyst');
    }
  };
};
