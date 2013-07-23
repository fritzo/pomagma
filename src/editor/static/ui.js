define(['log', 'views'],
function(log,   views)
{

var ui = {};

var handleKeydown = function (event) {
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
    $(window).off('keydown').on('keydown', handleKeydown);
  });
  $query.blur(function(){
    $(window).off('keydown');
  });
  $query.focus();
});

return ui;
});
