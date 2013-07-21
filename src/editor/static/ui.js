define(['log', 'views'],
function(log,   views)
{

var ui = {};

var handle_keydown = function (event) {
  console.log(event.which);
  switch (event.which) {
    case 13: // enter
      event.preventDefault();
      $('#query').blur();
      break;
  }
};

$(function(){

  var $query = ui.$query = $('#query');
  $query.focus(function(){
    $(window).off('keydown').on('keydown', handle_keydown);
  });
  $query.blur(function(){
    $(window).off('keydown');
  });
  $query.focus();
});

return ui;
});
