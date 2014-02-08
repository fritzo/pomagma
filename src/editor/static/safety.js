/**
 * Tools for safe coding.
 */

'use strict';

//----------------------------------------------------------------------------
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
// web workers

/** @constructor */
var WorkerException = function (message) {
  this.message = message || '(unspecified)';
};
WorkerException.prototype.toString = function () {
  return 'Worker Error: ' + this.message;
};
