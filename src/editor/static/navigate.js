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

  var namedEvents = (function(){

    var named = {};

    for (var name in keycode) {
      var which = keycode[name];
      named[name] = new KeyEvent(which);
      named['shift+' + name] = new KeyEvent(which, {'shift': true});
      named['ctrl+' + name] = new KeyEvent(which, {'ctrl': true});
    }

    _.forEach('ABCDEFGHIJKLMNOPQRSTUVWXYZ', function (name) {
      named[name] = named['shift+' + name.toLowerCase()];
    });

    named[' '] = named['space'];
    named['{'] = named['shift+openbracket'];
    named['\\'] = named['backslash'];
    named['/'] = named['slash'];
    named['|'] = named['shift+backslash'];
    named['='] = named['equal'];
    named['_'] = named['shift+minus'];
    named['.'] = named['period'];
    named['('] = named['shift+numpad9'];
    named[')'] = named['shift+numpad0'];

    return named;
  })();

  //--------------------------------------------------------------------------
  // Event handling

  var events = [];
  var callbacks = [];

  var on = function (name, callback, description) {
    assert(_.has(namedEvents, name), 'bad name: ' + name);
    events.push(namedEvents[name]);
    callbacks.push(callback);
    var picture = '<span>' + name.replace(/\+/g,'</span>+<span>') + '</span>';
    $('#navigate table').append(
      $('<tr>').append(
        $('<th>').html(picture),
        $('<td>').html(description)));
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
        return true;
      }
    }
    console.log('unmatched ' + event.which);
    return false;
  };

  //--------------------------------------------------------------------------
  // Interface

  return {
    on: on,
    off: off,
    trigger: trigger,
  };
});
