/**
 * Tools for safe coding.
 */

'use strict';

//------------------------------------------------------------------------------
// unfinished code

/** @constructor */
var TodoException = function (message) {
  this.message = message || '(unfinished code)';
};

TodoException.prototype.toString = function () {
  return 'TODO: ' + this.message;
};

var TODO = function (message) {
  throw new TodoException(message);
};

//----------------------------------------------------------------------------
// assertions

/** @constructor */
var AssertException = function (message) {
  this.message = message || '(unspecified)';
};

AssertException.prototype.toString = function () {
  return 'Assertion Failed: ' + this.message;
};

var assert = function (condition, message) {
  if (!condition) {
    throw new AssertException(message);
  }
};

assert.equal = function (actual, expected, message) {
  assert(_.isEqual(actual, expected),
    (message || '') +
    '\n    actual = ' + JSON.stringify(actual) +
    '\n    expected = ' + JSON.stringify(expected));
};

//----------------------------------------------------------------------------
// web workers

/** @constructor */
var WorkerException = function (message) {
  this.message = message || '(unspecified)';
};
WorkerException.prototype.toString = function () {
  return 'Worker Error: ' + this.message;
};
