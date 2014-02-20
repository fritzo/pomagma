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
  console.warn('WARNING ' + message);
};

var ServerError = function (messages) {
  this.messages = messages;
};
ServerError.prototype.toString = function () {
  return 'Server Errors:\n' + this.messagess.join('\n');
};

// FIXME This is not robust and will not work under heavy load.
// A possible workaround would be to create a pool of zmq routers.
// Another possible workaround is to thread routing through the analyst.
// see http://stackoverflow.com/questions/12544612
var router = function (socket) {
  return function (request, done) {
    socket.once('message', done);
    socket.send(request);
  };
};

exports.connect = function (address) {
  'use strict';
  assert(typeof address === 'string', address);
  var socket = zmq.socket('req');
  console.log('connecting to analyst at ' + address);
  socket.connect(address);

  var rawCall = router(socket);
  var call = function (request, done) {
    var rawRequest = new Request(request).toBuffer();
    console.log('DEBUG send ' + JSON.stringify(Request.decode(rawRequest)));
    rawCall(rawRequest, function(rawReply){
      var reply = Response.decode(rawReply);
      console.log('DEBUG receive ' + JSON.stringify(reply));
      reply.error_log.forEach(WARN);
      _.forEach(request, function(val, key){
        assert(reply[key] !== null, key);
      });
      if (reply.error_log.length) {
        throw new ServerError(reply.error_log);
      }
      done(reply);
    });
  };

  var ping = function (done) {
    call({}, function(){
      done();
    });
  };

  var testInference = function (done) {
    call({test_inference: {}}, function(reply){
      done(reply.test_inference.fail_count.toInt());
    });
  };

  var simplify = function (codes, done) {
    call({simplify: {codes: codes}}, function(reply){
      done(reply.simplify.codes);
    });
  };

  var validateCorpus = function (lines, done) {
    call({validate_corpus: {lines: lines}}, function(reply){
      var results = reply.validate_corpus.results;
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
    simplify: simplify,
    validateCorpus: validateCorpus,
    close: function() {
      socket.close();
      console.log('disconnected from pomagma analyst');
    }
  };
};
