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
var example_line = {
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
    var refs_name = refs[name] || {};
    refs_name[id] = null;
    _refs[name] = refs_name;
  };

  var removeRef = function (name, id) {
    var refs_name = refs[name];
    assert(refs_name !== undefined);
    assert(refs_name[id] != undefined);
    delete refs_name[id];
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
    var name = line.name;
    if (name !== null) {
      insertDef(name, id);
    }
    line.refs.forEach(function(name){
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
    for (var id in linesToLoad) {
      insertLine(linesToLoad[id]);
    }
  };

  var init = function () {
    $.ajax({
      url: 'corpus',
      cache: false
    }).fail(function(_, textStatus){
      log('Request failed: ' + textStatus);
    }).done(function(msg){
      loadAll(msg.lines);
    });
  };

  state.insert = function (line) {
    $.ajax({
      url: 'corpus/create_hole',
      cache: false
    }).fail(function(_, textStatus){
      log('Request failed: ' + textStatus);
    }).done(function(msg){
      log('created line: ' + msg.id);
      line.id = msg.id;
      insertLine(line);
      sync.update(line);
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

  state.find_all = function () {
    var result = [];
    for (var id in lines) {
      result.push(id);
    }
    return result;
  };

  state.find_def = function (name) {
    var id = defs[name];
    if (id !== undefined) {
      return id;
    } else {
      return null;
    }
  };

  state.find_refs = function (name) {
    var refs_name = refs[name];
    if (refs_name === undefined) {
      return [];
    } else {
      var refs_list = [];
      for (var id in refs_name) {
        refs_list.push(id);
      }
      return refs_list;
    }
  };

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

corpus.find_all = state.find_all;
corpus.find_def = state.find_def;

return corpus;
})();
