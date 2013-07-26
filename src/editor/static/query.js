define(['log', 'editor'],
function(log,   editor)
{
  var query = {};

  var handleKeydown = function (event) {
    console.log(event.which);
    switch (event.which) {
      case 9: // tab
        $('#query').blur();
        event.preventDefault();
        break;

      case 13: // enter
        $('#query').blur();
        event.preventDefault();
        break;
    }
  };

  $(function(){
    $('#query').focus(function(){
      editor.blur();
      $(window).off('keydown').on('keydown', handleKeydown);
    });
    $('#query').blur(function(){
      editor.focus();
    });
  });

  return query;
});
