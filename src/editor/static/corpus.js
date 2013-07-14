/**
 * Corpus of lines of code.
 *
 * FIXME this is all concurrency-unsafe; client assumes it is the only writer.
 */

var corpus = (function(){
var corpus = {};

IDENTIFIER_RE = /^[^\d\W]\w*(\.[^\d\W]\w*)*$/;
KEYWORD_RE = /^[A-Z]+$/;

test('assert("asdf".match(IDENTIFIER_RE))');
test('assert(!"asdf".match(KEYWORD_RE))');
test('assert("ASDF".match(IDENTIFIER_RE))');
test('assert("ASDF".match(KEYWORD_RE))');

//----------------------------------------------------------------------------
// client state

/*
var exampleLine = {
  'id': 'asfgvg1tr457et46979yujkm',
  'name': 'div',      // or null for anonymous lines
  'code': 'APP V K',  // compiled code
  'free': {}          // set of free variables in this line : string -> null
};
*/

var state = (function(){
  var state = {};

  // FIXME these maps fail with names like 'constructor';
  //   maybe fix by requiring a '.' in all names in corpus.
  var lines = {};  // id -> line
  var definitions = {};  // name -> id
  var occurrences = {};  // name -> (set id)

  var insertOccurrence = function (name, id) {
    var occurrencesName = occurrences[name] || {};
    occurrencesName[id] = null;
    occurrences[name] = occurrencesName;
  };

  var removeOccurrence = function (name, id) {
    var occurrencesName = occurrences[name];
    assert(occurrencesName !== undefined);
    assert(occurrencesName[id] != undefined);
    delete occurrencesName[id];
  };

  var insertDefinition = function (name, id) {
    assert(definitions[name] === undefined);
    definitions[name] = id;
  };

  var updateDefinition = function (name, id) {
    assert(definitions[name] !== undefined);
    definitions[name] = id;
  };

  var removeDefinition = function (name) {
    assert(definitions[name] !== undefined);
    assert(!occurrences[name]);
    delete definitions[name];
    delete occurrences[name];
  };

  var insertLine = function (line) {
    var id = line.id;
    log('loading line ' + id);
    lines[id] = line;
    var name = line.name;
    if (name !== null) {
      insertDefinition(name, id);
    }
    free = {}
    var tokens = line.code.split(/\s/);
    tokens.forEach(function(token){
      assert(token.match(IDENTIFIER_RE));
      if (!token.match(KEYWORD_RE)) {
        free[token] = null;
      }
    });
    for (var name in free) {
      insertOccurrence(name, id);
    }
  };

  var removeLine = function (line) {
    TODO('remove line');
  };

  var loadAll = function (linesToLoad) {
    lines = {};
    definitions = {};
    occurrences = {};
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

  state.findLine = function (id) {
    var line = lines[id];
    return {
      name: line.name,
      code: line.code,
      free: $.clone(line.free)
    };
  };

  state.findAllLines = function () {
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

  state.findDefinition = function (name) {
    var id = definitions[name];
    if (id !== undefined) {
      return id;
    } else {
      return null;
    }
  };

  state.findOccurrences = function (name) {
    var occurrencesName = occurrences[name];
    if (occurrencesName === undefined) {
      return [];
    } else {
      var occurrencesList = [];
      for (var id in occurrencesName) {
        occurrencesList.push(id);
      }
      return occurrencesList;
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

corpus.findLine = state.findLine;
corpus.findAllLines = state.findAllLines;
corpus.findAllNames = state.findAllNames;
corpus.findDefinition = state.findDefinition;
corpus.findOccurrences = state.findOccurrences;

return corpus;
})();
