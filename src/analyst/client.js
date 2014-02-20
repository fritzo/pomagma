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

// This works around zeromq.node's inconvenient req-rep interface.
// see http://stackoverflow.com/questions/12544612
var router = function (socket) {
  var callbacks = {};
  var nextId = 0;

  var send = function (request, done) {
    var id = '' + nextId++;
    callbacks[id] = done;
    request.id = id;
    var rawRequest = new Request(request).toBuffer();
    console.log('SEND ' + JSON.stringify(Request.decode(rawRequest)));
    socket.send(rawRequest);
  };

  var recv = function (rawReply) {
    var reply = Response.decode(rawReply);
    console.log('RECV ' + JSON.stringify(reply));
    var id = reply.id;
    assert(id !== null);
    delete reply.id;
    var done = callbacks[id];
    delete callbacks[id];
    done(reply);
  };

  socket.on('message', recv);
  return send;
};

exports.connect = function (address) {
  'use strict';
  assert(_.isString(address), address);
  var socket = zmq.socket('req');
  console.log('connecting to analyst at ' + address);
  socket.connect(address);

  var callUnsafe = router(socket);
  var call = function (request, done) {
    var keys = _.keys(request);
    callUnsafe(request, function(reply){
      reply.error_log.forEach(WARN);
      keys.forEach(function(key){
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

  var simplify = function (codes, done) {
    assert(_.isArray(codes), codes);
    codes.forEach(function(code){
      assert(_.isString(code), code);
    });
    call({simplify: {codes: codes}}, function(reply){
      var results = reply.simplify.codes;
      assert(results.length == codes.length);
      done(results);
    });
  };

  var validate = function (codes, done) {
    assert(_.isArray(codes), codes);
    codes.forEach(function(code){
      assert(_.isString(code), code);
    });
    call({validate: {codes: codes}}, function(reply){
      var results = reply.validate.results;
      assert(results.length == codes.length);
      results.forEach(function(line){
        line.is_top = TROOL[line.is_top];
        line.is_bot = TROOL[line.is_bot];
      });
      done(results);
    });
  };

  var validateCorpus = function (lines, done) {
    assert(_.isArray(lines), lines);
    lines.forEach(function(line){
      assert(_.isObject(line), line);
      var keys = _.keys(line);
      keys.sort();
      assert.deepEqual(keys, ['code', 'name']);
      assert(line.name === null || _.isString(line.name), line.name);
      assert(_.isString(line.code), line.code);
    });
    call({validate_corpus: {lines: lines}}, function(reply){
      var results = reply.validate_corpus.results;
      assert(results.length == lines.length);
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
    simplify: simplify,
    validate: validate,
    validateCorpus: validateCorpus,
    close: function() {
      socket.close();
      console.log('disconnected from pomagma analyst');
    }
  };
};
