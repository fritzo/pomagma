/**
 * Corpus of lines of code.
 *
 * FIXME this is all concurrency-unsafe; client assumes it is the only writer.
 */

define(['log', 'test', 'symbols'],
function(log,   test,   symbols)
{
  var corpus = {};

  var getFreeVariables = function (code) {
    var free = {};
    var prevToken = null;
    code.split(/\s+/).forEach(function(token){
      assert(symbols.isToken(token), 'invalid token: ' + token);
      if (!symbols.isKeyword(token)) {
        assert(symbols.isGlobal(token), 'invalid global: ' + token);
        free[token] = null;
      }
    });
    return free;
  };

  test('no-free-variables', function(){
    var code = 'APP J I';
    var free = {};
    assert.equal(getFreeVariables(code), free);
  });

  test('one-free-variables', function(){
    var code = 'APP CI types.div';
    var free = {'types.div': null};
    assert.equal(getFreeVariables(code), free);
  });

  test('many-free-variables', function(){
    var code = 'APP APP P COMP types.div types.semi types.div';
    var free = {'types.div': null, 'types.semi': null};
    assert.equal(getFreeVariables(code), free);
  });

  //--------------------------------------------------------------------------
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
      if (line.name !== null) {
        insertDefinition(line.name, id);
      }
      line.free = getFreeVariables(line.code);
      for (var name in line.free) {
        insertOccurrence(name, id);
      }
    };

    var removeLine = function (line) {
      TODO('remove line');
    };

    var readyQueue = [];
    state.ready = function (cb) {
      readyQueue.push(cb);
    };
    var markReady = function () {
      state.ready = function (cb) {
        setTimeout(cb, 0);
      };
      readyQueue.forEach(state.ready);
      readyQueue = [];
    };

    var loadAll = function (linesToLoad) {
      lines = {};
      definitions = {};
      occurrences = {};
      linesToLoad.forEach(insertLine);
      markReady();
    };

    var init = function () {
      $.ajax({
        type: 'GET',
        url: 'corpus/lines',
        cache: false
      }).fail(function(jqXHR, textStatus){
        log('Request failed: ' + textStatus);
      }).done(function(data){
        loadAll(data.data);
      });
    };

    state.insert = function (line) {
      $.ajax({
        type: 'POST',
        url: 'corpus/line',
        data: line
      }).fail(function(jqXHR, textStatus){
        log('Request failed: ' + textStatus);
      }).done(function(data){
        log('created line: ' + data.id);
        line.id = data.data;
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

    state.validate = function () {
      log('validating corpus');
      for (var id in lines) {
        var line = lines[id];
        var name = line.name;
        if (line.name !== null) {
          assert(symbols.isGlobal(name), 'name is not global: ' + name);
          assert(!symbols.isKeyword(name), 'name is keyword: ' + name);
          assert(definitions[name] === line.id, 'missing definition: ' + name);
        }
        var free = getFreeVariables(line.code);
        assert.equal(line.free, free, 'wrong free variables:');
        for (var name in free) {
          assert(symbols.isGlobal(name), 'name is not global: ' + name);
          var occurrencesName = occurrences[name];
          assert(occurrencesName !== undefined, 'missing occurrences: ' + name);
          assert(occurrencesName[id] === null, 'missing occurrence: ' + name);
        }
      }
    };

    test('corpus valid', function(){ state.ready(state.validate); });

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

    state.DEBUG_lines = lines;

    init();
    return state;
  })();

  //--------------------------------------------------------------------------
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
            }).fail(function(jqXHR, textStatus){
              log('putChanges PUT failed: ' + textStatus);
              setTimeout(pushChanges, delay);
            }).done(function(){
              log('putChanges PUT succeeded: ' + id);
              setTimeout(pushChanges, 0);
            });
            return;

          case 'remove':
            $.ajax({
              type: 'DELETE',
              url: 'corpus/line/' + id
            }).fail(function(jqXHR, textStatus){
              log('putChanges DELETE failed: ' + textStatus);
              setTimeout(pushChanges, delay);
            }).done(function(){
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

  //--------------------------------------------------------------------------
  // interface

  corpus.validate = function () {
    state.validate();
  };

  corpus.findLine = state.findLine;
  corpus.findAllLines = state.findAllLines;
  corpus.findAllNames = state.findAllNames;
  corpus.findDefinition = state.findDefinition;
  corpus.findOccurrences = state.findOccurrences;

  return corpus;
});
