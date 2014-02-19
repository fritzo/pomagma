'use strict';
var client = require('./client.js');

exports.ADDRESS = (
  process.env.POMAGMA_ANALYST_ADDRESS || 'tcp://localhost:34936'
);

exports.connect = function (address) {
  return client.connect(address || exports.ADDRESS);
};
