/** 
 * Abstract syntax trees
 *
 *   expr ::= var
 *          | QUOTE expr
 *          | LET patt expr expr
 *            # allows recursion when fv(patt) appear in first expr
 *          | ABSTRACT patt expr
 *          | APPLY expr expr
 *          | JOINT expr expr
 *          | COMPOSE expr expr
 *          | BOX expr
 *          | HOLE
 *          | CURSOR expr
 *
 *   patt ::= var
 *          | QUOTE patt
 *          | BOX patt
 *          | TYPE patt expr
 *          | CURSOR patt
 */

var ast = (function(){
var ast = {};

//----------------------------------------------------------------------------
// Construction

var Hole = function () {
  this.below = [];
  this.above = null;
};

var Vary = function (name) {
  this.name = name;
  this.below = [];
  this.above = null;
};

var Abstract = function (patt, body) {
  this.below = [patt, body];
  this.above = null;
  patt.above = this;
  body.above = this;
};

var Let = function (patt, defn, body) {
  this.below = [patt, defn, body];
  this.above = null;
  patt.above = this;
  defn.above = this;
  body.above = this;
};

var Apply = function (fun, arg) {
  this.below = [fun, arg];
  this.above = null;
  fun.above = this;
  arg.above = this;
};

var Quote = function (body) {
  this.below = [body];
  this.above = null;
  body.above = this;
};

var Cursor = function (body) {
  this.below = [body];
  this.above = null;
  body.above = this;
};

//----------------------------------------------------------------------------
// Printing to polish notation

Hole.prototype.polish = function () {
  return 'HOLE';
};

Vary.prototype.polish = function () {
  return 'VARY ' + this.name;
};

Abstract.prototype.polish = function () {
  var patt = this.below[0];
  var body = this.below[1];
  return 'ABSTRACT ' + patt.polish() + ' ' + body.polish();
};

Let.prototype.polish = function () {
  var patt = this.below[0];
  var defn = this.below[1];
  var body = this.below[2];
  return 'LET ' + patt.polish() + ' ' + defn.polish() + ' ' + body.polish();
};

Apply.prototype.polish = function () {
  var fun = this.below[0];
  var arg = this.below[1];
  return 'APPLY ' + fun.polish() + ' ' + arg.polish();
};

Quote.prototype.polish = function () {
  var body = this.below[0]
  return 'QUOTE ' + body.polish();
};

Cursor.prototype.polish = function () {
  var body = this.below[0]
  return 'CURSOR ' + body.polish();
};

//----------------------------------------------------------------------------
// Parsing from polish notation

var Parser = function (string) {
  this.tokens = string.split(' ');
  this.pos = 0;
};

Parser.prototype.pop = function () {
  return this.tokens[this.pos++];
};

Parser.prototype.parse = function () {
  var head = this.pop();
  return parseHead[head](this);
};

var parseHead = {
  HOLE: function (state) {
    return new Hole();
  },
  VARY: function(state) {
    var name = state.pop();
    return new Vary(name);
  },
  ABSTRACT: function (state) {
    var patt = state.parse();
    var body = state.parse();
    return new Abstract(patt, body);
  },
  LET: function (state) {
    var patt = state.parse();
    var defn = state.parse();
    var body = state.parse();
    return new Let(patt, defn, body);
  },
  APPLY: function (state) {
    var fun = state.parse();
    var arg = state.parse();
    return new Apply(fun, arg);
  },
  QUOTE: function(state) {
    var body = state.parse();
    return new Quote(body);
  },
  CURSOR: function(state) {
    var body = state.parse();
    return new Cursor(body);
  }
};

var parse = function (string) {
  var parser = new Parser(string);
  return parser.parse();
};
ast.parse = parse;

test('Simple parsing', function(){
  var cases = [
    'VARY x',
    'QUOTE APPLY ABSTRACT CURSOR VARY x VARY x HOLE',
    'LET VARY i ABSTRACT VARY x VARY x APPLY VARY i VARY i',
    ];
  for (var i = 0; i < cases.length; ++i) {
    var string = cases[i];
    log('Parsing ' + string);
    var expr = parse(string);
    var polish = expr.polish();
    assertEqual(string, polish);
  }
});

//----------------------------------------------------------------------------
// Cursor movement

Cursor.prototype.remove = function () {
  var above = this.above;
  this.below[0].above = above;
  if (above) {
    var pos = above.below.indexOf(this);
    above.below[pos] = this.below[0];
    return pos;
  }
};

Cursor.prototype.insertBelow = function (above, pos) {
  var below = above.below[pos];
  above.below[pos] = this;
  this.above = above;
  below.above = this;
  this.below[0] = below;
};

Cursor.prototype.insertAbove = function (below) {
  this.below[0] = below;
  var above = below.above;
  below.above = this;
  this.above = above;
  if (above !== null) {
    var pos = above.below.indexOf(below);
    above.below.below[pos] = this;
  }
};

Cursor.prototype.tryMoveDown = function () {
  var pivot = this.below[0];
  if (pivot.below.length === 0) {
    return false;
  } else {
    this.remove();
    this.insertBelow(pivot, 0);
    return true;
  }
};

Cursor.prototype.tryMoveUp = function () {
  var pivot = this.above;
  if (pivot === null) {
    return false;
  } else {
    this.remove();
    var above = pivot.above;
    if (above === null) {
      this.insertAbove(pivot);
    } else {
      var pos = above.below.indexOf(pivot);
      this.insertBelow(above, pos);
    }
    return true;
  }
};

Cursor.prototype.tryMoveSideways = function (direction) {
  var pivot = this.above;
  if ((pivot === null) || (pivot.below.length === 1)) {
    return false;
  } else {
    var pos = this.remove();
    pos = (pos + direction + pivot.below.length) % pivot.below.length;
    this.insertBelow(pivot, pos);
    return true;
  }
};

Cursor.prototype.tryMoveLeft = function () {
  return this.tryMoveSideways(-1);
};

Cursor.prototype.tryMoveRight = function () {
  return this.tryMoveSideways(+1);
};

Cursor.prototype.tryMove = function (direction) {
  switch (direction) {
    case 'U': return this.tryMoveUp();
    case 'D': return this.tryMoveDown();
    case 'L': return this.tryMoveLeft();
    case 'R': return this.tryMoveRight();
  }
};

test('Cursor movement', function(){
  var string = 'ABSTRACT QUOTE VARY this APPLY VARY is APPLY VARY a VARY test';
  log('Traversing ' + string)
  var expr = parse(string);
  var cursor = new Cursor(expr);
  var path =  'UDDDLRULDRDLDUUUU';
  var trace = '01100011111101110';
  for (var i = 0; i < path.length; ++i) {
    assertEqual(cursor.tryMove(path[i]), Boolean(parseInt(trace[i])));
  }
});

ast.getRoot = function (expr) {
  while (expr.above !== null) {
    expr = expr.above;
  }
  return expr;
};

//----------------------------------------------------------------------------
// Transformations

Hole.prototype.transform = {
  VARY: function (cursor) {
  }
};

Vary.transform = {
  HOLE: function (cursor) {
    
  }
};

return ast;
})(); // ast
