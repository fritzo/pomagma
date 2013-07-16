importScripts('lib/underscore.js');
importScripts('lib/require.js');
importScripts('safety.js');

onmessage = function (message) {
  postMessage(message.data);
};
