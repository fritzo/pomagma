define(['log', 'test', 'keycode', 'compiler'],
function(log,   test,   keycode,   compiler){

  //--------------------------------------------------------------------------
  // Events

  /** @constructor */
  var KeyEvent = function (which, modifiers) {
    if (modifiers === undefined) {
      modifiers = {};
    }
    this.state = [
      which,
      modifiers.shift || false,
      modifiers.ctrl || false,
      modifiers.alt || false,
      modifiers.meta || false,
    ];
  };

  KeyEvent.prototype = {
    match: function (event, match) {
      var state = this.state;
      return (
        state[0] === event.which &&
        state[1] === event.shiftKey &&
        state[2] === event.ctrlKey &&
        state[3] === event.altKey &&
        state[4] === event.metaKey
      )
    }
  };

  var cases = {};
  var icons = {};
  (function(){
    for (var name in keycode) {
      var which = keycode[name];
      cases[name] = new KeyEvent(which);
      cases['shift+' + name] = new KeyEvent(which, {'shift': true});
      cases['ctrl+' + name] = new KeyEvent(which, {'ctrl': true});
    }

    _.forEach('ABCDEFGHIJKLMNOPQRSTUVWXYZ', function (name) {
      cases[name] = cases['shift+' + name.toLowerCase()];
    });

    cases[' '] = cases['space'];
    cases['{'] = cases['shift+openbracket'];
    cases['\\'] = cases['backslash'];
    cases['/'] = cases['slash'];
    cases['|'] = cases['shift+backslash'];
    cases['='] = cases['equal'];
    cases['<'] = cases['shift+comma'];
    cases['>'] = cases['shift+period'];
    cases['_'] = cases['shift+dash'];
    cases['.'] = cases['period'];
    cases['('] = cases['shift+9'];
    cases[')'] = cases['shift+0'];
    cases['?'] = cases['shift+slash'];
    cases['.'] = cases['period'];

    for (var name in cases) {
      icons[name] = $('<th>').html(
        '<span>' + name.replace(/\+/g, '</span>+<span>') + '</span>'
      );
    };
  })();

  //--------------------------------------------------------------------------
  // Event Handling

  var events = [];
  var callbacks = [];

  var on = function (name, callback, description) {
    assert(_.has(cases, name));
    events.push(cases[name]);
    callbacks.push(callback);
    if (description !== undefined) {
      $('#navigate table').append(
        $('<tr>').append(icons[name], $('<td>').html(description)));
    }
  };

  var off = function () {
    events = [];
    callbacks = [];
    $('#navigate').empty().append($('<table>'));
  };

  var trigger = function (event) {
    for (var i = 0; i < events.length; ++i) {
      if (events[i].match(event)) {
        event.preventDefault();
        console.log('matched ' + event.which);
        callbacks[i]();
        return;
      }
    }
    console.log('unmatched ' + event.which);
  };

  //--------------------------------------------------------------------------
  // Global Variables

  var search = (function(){
    var strings = [];
    var $input = undefined;
    var matches = [];
    var $matches = undefined;

    var VAR = compiler.symbols.VAR;

    var update = function () {
      var re = new RegExp($input.val());
      matches = [];
      $matches.empty();
      strings.forEach(function (string) {
        if (re.test(string)) {
          matches.push(string);
          $matches.append($('<pre>').html(compiler.render(VAR(string))));
        }
      });
      log('DEBUG ' + matches);
    };

    var cancelCallback;
    var acceptCallback;
    var accept = function () {
      if (matches.length) {
        log('DEBUG accepting ' + matches[0]);
        acceptCallback(matches[0]);
      } else {
        cancelCallback();
      }
    };

    return function (rankedStrings, acceptMatch, cancel) {
      strings = rankedStrings;
      acceptCallback = acceptMatch;
      cancelCallback = cancel;

      off();
      on('enter', accept, 'accept');
      on('tab', cancel, 'cancel');
      $input = $('<input>');
      $matches = $('<div>');
      $('#navigate').append($input, $matches);
      $input.focus().on('keydown', _.debounce(update));
      update();
    };
  })();

  var choose = (function(){
    var $input = undefined;
    var input = undefined;
    var isValid = undefined;
    var valid = undefined;

    var update = function () {
      input = $input.val();
      valid = isValid(input);
      $input.attr({'class': valid ? 'valid' : 'invalid'});
    };

    var cancelCallback;
    var acceptCallback;
    var accept = function () {
      if (valid) {
        log('DEBUG choosing ' + input);
        acceptCallback(input);
      } else {
        cancelCallback();
      }
    };

    return function (isValidFilter, acceptName, cancel) {
      isValid = isValidFilter;
      acceptCallback = acceptName;
      cancelCallback = cancel;

      off();
      on('enter', accept, 'accept');
      on('tab', cancel, 'cancel');
      $input = $('<input>');
      $('#navigate').append($input);
      $input.focus().on('keydown', _.debounce(update));
      update();
    };
  })();

  //--------------------------------------------------------------------------
  // Interface

  return {
    on: on,
    off: off,
    search: search,
    choose: choose,
    trigger: trigger,
  };
});
