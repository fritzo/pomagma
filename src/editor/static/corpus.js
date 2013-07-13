/**
 * Corpus of lines of code.
 *
 * FIXME this is all concurrency-unsafe; client assumes it is the only writer.
 */

var corpus = (function(){
var corpus = {};

//----------------------------------------------------------------------------
// client state

/*
var exampleLine = {
  'id': 'asfgvg1tr457et46979yujkm',
  'name': 'div',      // or null for anonymous lines
  'code': 'APP V K',  // compiled code
  'args': []          // names which this line referencess, list w/o repeats
};
*/

var state = (function(){
  var state = {};

  var lines = {};  // id -> line
  var defs = {};  // name -> id
  var refs = {};  // name -> (set id)

  var insertRef = function (name, id) {
    var refsName = refs[name] || {};
    refsName[id] = null;
    _refs[name] = refsName;
  };

  var removeRef = function (name, id) {
    var refsName = refs[name];
    assert(refsName !== undefined);
    assert(refsName[id] != undefined);
    delete refsName[id];
  };

  var insertDef = function (name, id) {
    assert(defs[name] === undefined);
    defs[name] = id;
  };

  var updateDef = function (name, id) {
    assert(defs[name] !== undefined);
    defs[name] = id;
  };

  var removeDef = function (name) {
    assert(defs[name] !== undefined);
    assert(!refs[name]);
    delete defs[name];
    delete refs[name];
  };

  var insertLine = function (line) {
    var id = line.id;
    log('DEBUG inserting ' + id);
    lines[id] = line;
    var name = line.name;
    if (name !== null) {
      insertDef(name, id);
    }
    line.args.forEach(function(name){
      insertRef(name, id);
    });
  };

  var removeLine = function (line) {
    TODO('remove line');
  };

  var loadAll = function (linesToLoad) {
    lines = {};
    defs = {};
    refs = {};
    linesToLoad.forEach(insertLine);
  };

  var init = function () {
    $.ajax({
      type: 'GET',
      url: 'corpus/lines',
      cache: false
    }).fail(function(_, textStatus){
      log('Request failed: ' + textStatus);
    }).done(function(msg){
      loadAll(msg.data);
    });
  };

  state.insert = function (line) {
    $.ajax({
      type: 'POST',
      url: 'corpus/line',
      data: line
    }).fail(function(_, textStatus){
      log('Request failed: ' + textStatus);
    }).done(function(msg){
      log('created line: ' + msg.id);
      line.id = msg.data;
      insertLine(line);
    });
  };

  state.update = function (newline) {
    var id = newline.id;
    var line = lines[id];
    TODO('replace old object with new');
    sync.update(line);
  };

  state.remove = function (id) {
    var line = lines[id];
    assert(line !== undefined);
    removeLine(line);
    sync.remove(line);
  };

  state.find = function (id) {
    var line = lines[id];
    return {
      name: line.name,
      code: line.code,
      args: line.args.slice(0)
    };
  };

  state.findAll = function () {
    var result = [];
    for (var id in lines) {
      result.push(id);
    }
    return result;
  };

  state.findAllNames = function () {
    var result = [];
    for (var id in lines) {
      var name = lines[id].name;
      if (name) {
        result.push(name);
      }
    }
    return result;
  };

  state.findDef = function (name) {
    var id = defs[name];
    if (id !== undefined) {
      return id;
    } else {
      return null;
    }
  };

  state.findRefs = function (name) {
    var refsName = refs[name];
    if (refsName === undefined) {
      return [];
    } else {
      var refsList = [];
      for (var id in refsName) {
        refsList.push(id);
      }
      return refsList;
    }
  };

  corpus.DEBUG_lines = lines;

  init();
  return state;
})();

//----------------------------------------------------------------------------
// change propagation

var sync = (function(){
  var sync = {};

  var changes = {};

  sync.update = function (line) {
    changes[line.id] = {type: 'update', line: line};
  };

  sync.remove = function (line) {
    changes[line.id] = {type: 'remove'};
  };

  var delay = 1000;

  var pushChanges = function () {
    for (id in changes) {
      var change = changes[id];
      delete changes[id];
      switch (change.type) {
        case 'update':
          $.ajax({
            type: 'PUT',
            url: 'corpus/line/' + id,
            data: change.line
          }).fail(function(_, textStatus){
            log('putChanges PUT failed: ' + textStatus);
            setTimeout(pushChanges, delay);
          }).done(function(msg){
            log('putChanges PUT succeeded: ' + id);
            setTimeout(pushChanges, 0);
          });
          return;

        case 'remove':
          $.ajax({
            type: 'DELETE',
            url: 'corpus/line/' + id
          }).fail(function(_, textStatus){
            log('putChanges DELETE failed: ' + textStatus);
            setTimeout(pushChanges, delay);
          }).done(function(msg){
            log('putChanges DELETE succeeded: ' + id);
            setTimeout(pushChanges, 0);
          });
          return;

        default:
          log('ERROR unknown change type: ' + change.type)
      }
    }
    setTimeout(pushChanges, delay);
  };

  var init = function () {
    setTimeout(pushChanges, 0);
  };

  init();
  return sync;
})();

//----------------------------------------------------------------------------
// interface

corpus.find = state.find;
corpus.findAll = state.findAll;
corpus.findAllNames = state.findAllNames;
corpus.findDef = state.findDef;
corpus.findRefs = state.findRefs;

return corpus;
})();
