define(function(require){
  'user strict';

  var $ = require('lib/jquery');
  var log = require('log');
  var test = require('test');
  var corpus = require('corpus');
  var analyst = require('analyst');
  var editor = require('editor');

  var ready = function (cb) {
    $(function(){
      corpus.ready(cb);
    });
  };

  var testMain = function () {
    var oldTitle = document.title;
    document.title = 'Test - ' + oldTitle;
    test.runAll(function(){
      document.title = oldTitle;
      window.location.hash = '';
      editor.main();
    });
  };

  if (window.location.hash && window.location.hash.substr(1) === 'test') {
    ready(testMain);
  } else {
    ready(editor.main);
  }
});
