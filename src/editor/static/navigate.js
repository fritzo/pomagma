define(['log', 'test', 'keycode'],
function(log,   test,   keycode){

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
    cases['_'] = cases['shift+minus'];
    cases['.'] = cases['period'];
    cases['('] = cases['shift+9'];
    cases[')'] = cases['shift+0'];

    for (var name in cases) {
      icons[name] = $('<th>').html(
        '<span>' + name.replace(/\+/g, '</span>+<span>') + '</span>'
      );
    };
  })();

  //--------------------------------------------------------------------------
  // Event handling

  var events = [];
  var callbacks = [];

  var on = function (name, callback, description) {
    assert(_.has(cases, name));
    events.push(cases[name]);
    callbacks.push(callback);
    $('#navigate table').append(
      $('<tr>').append(icons[name], $('<td>').html(description)));
  };

  var off = function () {
    events = [];
    callbacks = [];
    $('#navigate').empty().append($('<table>'));
  };

  var trigger = function (event) {
    for (var i = 0; i < events.length; ++i) {
      if (events[i].match(event)) {
        console.log('matched ' + event.which);
        callbacks[i]();
        event.preventDefault();
        return;
      }
    }
    console.log('unmatched ' + event.which);
  };

  //--------------------------------------------------------------------------
  // Interface

  return {
    on: on,
    off: off,
    trigger: trigger,
  };
});
