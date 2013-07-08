var corpus = (function(){
var corpus = {};

corpus.listModules = function (cb) {
  $.ajax({
    url: 'corpus',
    cache: false
  }).done(function(msg){
    cb(msg.modules);
  }).fail(function(_, textStatus){
    alert('Request failed: ' + testStatus);
  });
};

corpus.loadModule = function (name, cb) {
  $.ajax({
    url: 'corpus/' + name,
    cache: false
  }).done(function(msg){
    cb(msg.module);
  }).fail(function(msg){
    cb(null);
  });
};

corpus.storeModule = function (name, value) {
  $.ajax({
    type: 'PUT',
    url: 'corpus/' + name,
    data: value
  }).done(function(msg){
    cb(msg.responseJSON.module);
  }).fail(function(_, testStatus){
    alert('Request failed: ' + testStatus);
  });
};

return corpus;
})(); // corpus
