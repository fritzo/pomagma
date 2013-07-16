define([],
function()
{

var views = {};

var sortLines = function (lineSet) {
  /*
  Return a heuristically sorted list of definitions.

  TODO use approximately topologically-sorted order.
  (R1) "A Technique for Drawing Directed Graphs" -Gansner et al
    http://www.graphviz.org/Documentation/TSE93.pdf
  (R2) "Combinatorial Algorithms for Feedback Problems in Directed Graphs"
    -Demetrescu and Finocchi
    http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.1.9435
  */
  lineArray = [];
  for (var id in lineSet) {
    lineArray.push(lineSet[id]);
  }
  return lineArray;
};

return views;
});
