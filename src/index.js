'use strict';

var path = require('path');

exports.util = {
  DATA: path.resolve(__dirname, '..', 'data'),

  LOG_LEVEL: parseInt(process.env.POMAGMA_LOG_LEVEL || 0),
  LOG_LEVEL_ERROR: 0,
  LOG_LEVEL_WARNING: 1,
  LOG_LEVEL_INFO: 2,
  LOG_LEVEL_DEBUG: 3
};

exports.analyst = require('./analyst/index.js');
