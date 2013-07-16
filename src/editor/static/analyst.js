define(['log'],
function(log)
{
  var analyst = {};

  var worker = new Worker('static/analystworker.js');
  worker.addEventListener('message', function(event){
    // TODO do something with event.data
  });
  worker.addEventListener('error', function(error){
    log('worker error: ' + error.message);
    throw error;
  });

  worker.postMessage({action: 'init'});

  return analyst;
});
