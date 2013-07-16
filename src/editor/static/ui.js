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
    $query.css('border-color', '#fb7');
    $(window).off('keydown').on('keydown', handle_keydown);
  });
  $query.blur(function(){
    $query.css('border-color', '#777');
    $(window).off('keydown');
  });
  $query.focus();
});

return ui;
});
