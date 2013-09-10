/**
 * Corpus of lines of code.
 *
 * FIXME this is all concurrency-unsafe; client assumes it is the only writer.
 */

define(['log', 'test', 'symbols'],
function(log,   test,   symbols)
{
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

    var insertDefinition = function (name, id) {
      assert(definitions[name] === undefined);
      assert(occurrences[name] === undefined);
      definitions[name] = id;
      occurrences[name] = {};
    };

    var updateDefinition = function (name, id) {
      assert(definitions[name] !== undefined);
      definitions[name] = id;
    };

    var insertOccurrence = function (name, id) {
      var occurrencesName = occurrences[name];
      assert(occurrencesName !== undefined);
      assert(occurrencesName[id] === undefined);
      occurrences[name][id] = null;
    };

    var removeOccurrence = function (name, id) {
      var occurrencesName = occurrences[name];
      assert(occurrencesName !== undefined);
      assert(occurrencesName[id] !== undefined);
      delete occurrencesName[id];
    };

    var removeDefinition = function (name) {
      assert(definitions[name] !== undefined);
      assert(occurrences[name] !== undefined);
      assert(_.isEmpty(occurrences[name]));
      delete definitions[name];
      delete occurrences[name];
    };

    var insertLine = function (line) {
      var id = line.id;
      assert(!_.has(lines, id));
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
      var id = line.id;
      assert(_.has(lines, id));
      delete lines[id];
      for (var name in line.free) {
        removeOccurrence(name, id);
      }
      if (line.name !== null) {
        removeDefinition(line.name);
      }
    };

    state.ready = (function(){
      var isReady = false;
      var readyQueue = [];
      var ready = function (cb) {
        if (isReady) {
          setTimeout(cb, 0);
        } else {
          readyQueue.push(cb);
        }
      };
      ready.set = function () {
        log('corpus is ready');
        isReady = true;
        while (readyQueue.length) {
          setTimeout(readyQueue.pop(), 0);
        }
      };
      return ready;
    }());

    var loadAll = function (linesToLoad) {
      lines = {};
      definitions = {};
      occurrences = {};
      linesToLoad.forEach(function(line){
        var id = line.id;
        lines[id] = line;
        if (line.name !== null) {
          insertDefinition(line.name, id);
        }
      });
      linesToLoad.forEach(function(line){
        var id = line.id;
        line.free = getFreeVariables(line.code);
        for (var name in line.free) {
          insertOccurrence(name, id);
        }
      });
      state.ready.set();
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

    state.insert = function (line, done, fail) {
      // FIXME getting an id from the server like this adds latency
      //   and prevents offline creation of lines
      assert(!_.has(line, 'id'), 'unexpected .id field in inserted line');
      $.ajax({
        type: 'POST',
        url: 'corpus/line',
        data: JSON.stringify(line),
        contentType: 'application/json',
      }).fail(function(jqXHR, textStatus){
        log('Request failed: ' + textStatus);
        fail();
      }).done(function(data){
        log('created line: ' + data.id);
        line.id = data.data;
        insertLine(line);
        done(line);
      });
    };

    state.update = function (newline) {
      var id = newline.id;
      assert(id !== undefined, 'expected .id field in updated line');
      var line = lines[id];
      assert(line !== undefined, 'bad id: ' + id);
      for (var name in line.free) {
        removeOccurrence(name, id);
      }
      line.code = newline.code;
      line.free = getFreeVariables(line.code);
      for (var name in line.free) {
        insertOccurrence(name, id);
      }
      sync.update(line);
      return line;
    };

    state.remove = function (id) {
      assert(_.has(lines, id));
      var line = lines[id];
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
          assert(
            occurrencesName !== undefined,
            'missing occurrences: ' + name);
          assert(occurrencesName[id] === null, 'missing occurrence: ' + name);
        }
      }
      log('corpus is valid');
    };

    test.async('corpus.validate', function(done){
      state.ready(function(){
        state.validate();
        done();
      });
    });

    state.findLine = function (id) {
      var line = lines[id];
      return {
        name: line.name,
        code: line.code,
        free: _.extend({}, line.free)
      };
    };

    state.findAllLines = function () {
      return _.keys(lines);
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
      assert(_.has(definitions, name));
      return _.keys(occurrences[name]);
    };

    state.hasOccurrences = function (name) {
      assert(_.has(definitions, name));
      return !_.isEmpty(occurrences[name]);
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
    var delayFail = 30000;

    var pushChanges = function () {
      for (id in changes) {
        var change = changes[id];
        delete changes[id];
        switch (change.type) {
          case 'update':
            log('sending ' + JSON.stringify(change.line));
            $.ajax({
              type: 'PUT',
              url: 'corpus/line/' + id,
              data: JSON.stringify(change.line),
              contentType: 'application/json',
            }).fail(function(jqXHR, textStatus){
              log('putChanges PUT failed: ' + textStatus);
              setTimeout(pushChanges, delayFail);
            }).done(function(){
              log('putChanges PUT succeeded: ' + id);
              setTimeout(pushChanges, 0);
            });
            return;

          case 'remove':
            $.ajax({
              type: 'DELETE',
              url: 'corpus/line/' + id,
            }).fail(function(jqXHR, textStatus){
              log('putChanges DELETE failed: ' + textStatus);
              setTimeout(pushChanges, delayFail);
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

  return {
    ready: state.ready,
    validate: state.validate,
    findLine: state.findLine,
    findAllLines: state.findAllLines,
    findAllNames: state.findAllNames,
    findDefinition: state.findDefinition,
    findOccurrences: state.findOccurrences,
    hasOccurrences: state.hasOccurrences,
    insert: state.insert,
    update: state.update,
    remove: state.remove,
  };
});
