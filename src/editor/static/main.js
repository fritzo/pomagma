require(['corpus', 'editor'],
function( corpus,   editor )
{
  test('corpus loaded', function(){
    assert(corpus !== undefined, 'corpus not loaded');
  });
  test('editor loaded', function(){
    assert(editor !== undefined, 'corpus not loaded');
  });

  var main = function () {
    // TODO
  };

  if (window.location.hash && window.location.hash.substr(1) === 'test') {

    document.title = 'Pomagma Editor Test';
    test.runAll(function(){
          document.title = 'Pomagma Editor';
          window.location.hash = '';
          main();
        });

  } else {

    main();

  }

});
