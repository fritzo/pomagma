importScripts('lib/underscore.js');
importScripts('lib/require.js');
require(['assert'], function(assert){

  onmessage = function (message) {
    postMessage(message.data);
  };
});
