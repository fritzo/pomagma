# Pomagma

## An experiment in Extensional Programming

The [Pomagma](https://github.com/fritzo/pomagma)
is an extensional programming environment
for developing computational behaviors.

Extensionality is the idea that two programs can be considered equal
if their input-output pairs are all equal,
in particular ignoring resource usage, run-time complexity, and space.
The opposite of extensionality is intensionality, the idea that programs
should be considered equal only if they convey the same concept intended
by the programmer.
Modern programming is mired in far-too intensional practices,
where incidental artifacts of code
(whitespace, style, line order, local variable names, arbitrary imperatives)
frustrate many actions that would be easier with an extensional view
(code-search, verification, optimization, automatic parallelization).
Better programming practice might start with
syntax-directed editors, tools for code refactoring,
purely functional and declarative languages,
and precise type systems.
But a key missing concept is the use of extensionality.
Pomagma is an experiment to see how far extensionality can be pushed.

Pomagma is founded on a simple untyped pure functional programming language,
the non-deterministic &lambda;-calculus <a href="#user-content-1">[1]</a>,
and a "maximally-coarse" semantics <a href="#user-content-2">[2]</a>
where as many programs as possible
are considered equal.
At the core of the Pomagma system is an inference engine
that is used for verification and search/suggestion.

### Language: the &lambda;-join-calculus

The &lambda;-join-calculus is a &lambda;-calculus with a join operation,
written `x|y` indicating nondeterministic or concurrent choice.
We think of join as concurrency in the sense that
`x|y` halts iff either of `x` or `y` halt.
Nondeterminism allows one to specify what doesn't matter in a program:
symmetry, order of decoupled operations, etc.

### Semantics: observational equivalence

Naively, two programs might be considered equal if their outputs agree at all inputs.
However, in a space where programs can be applied to programs,
and where programs may sometimes halt,
one needs to define this equational semantics carefully by coinduction.
It turns out to be be enough to say that two programs `x` and `y` are equal
iff for every program `f`, `f x` halts iff `f y` halts
(or when modeling probabilistic programs,
that `f x` halts exactly as often as `f y` halts).

### Type System: nondeterministic polymorphism

Pomagma provides a rich type system by simulating types within the base system.
The first idea, due to Dana Scott <a href="#user-content-3">[3]</a>,
is to define a term `x` to have type `t`
iff `x` is a fixed-point of `t`, i.e., `x:t` iff `t x = x`.
The second idea, from <a href="#user-content-4">[4]</a>,
is to use the combination of non-determinism and
observational equivalence to define higher-order polymorphic types `t`
inside the untyped base language.

### Reflection: extensional quoting

Pomagma takes an extensional approach to quoting.
Opposite to Kleene's intensional quoting convention,
where codes `x` are considered intensional and were evaluated `{x}`
to produce functions, Pomagma's language treats codes `x` as
extensional and requires quoting `{x}` to prevent evaluation.
Moreover by consistently extending the &lambda;-join-calculus,
we can achieve the rule: if it is provable that `x = y`, then also `{x} = {y}`.
In Pomagma, quoting serves to flatten the information ordering,
rather than preserve intension.

### Logical strength: predicative mathematics

Pomagma consistently extends &lambda;-join-calculus with
a partial equation-deciding oracle.
This allows equations to be interpreted back into the language as terms.
Iterating, we can thus write equations of strength all the way up the
hyperarithmetic hierarchy to &Delta;<sub>1</sub><sup>1</sup>,
and provide a foundation for all of Sol Feferman's predicative mathematics
<a href="#user-content-5">[5]</a>.

### Code Format: a database of definitions and assertions

Pomagma's coding interface minimizes intensional data.
Rather than a file of lines of code,
Pomagma stores a database of unordered lines of code.
Each line is either a definition (an explicit declaration)
or an assertion (an implicit declaration).
All defined variables are globally visible.
The behavior of a line of code as a function of its referenced global variables
is treated extensionally.
Lines are stored in "compiled" form and are "decompiled" on the fly while editing.
Multi-line views of code are also generated on the fly by querying the line database.
(Contrast this with the archaic tree-of-files-of-lines-of-code format
that this very repo is stored in.)

<hr/>

- [1] <a name="1"/>
  the &lambda;-join-calculus in terms of Scott's information ordering.
- [2] <a name="2"/>
  Hyland and Wadsworth's &lambda;-theory
  <it>H</it><sup>&#42;</sup> of observational equivalence,
  the equational theory of Scott's D<sub>&#8734;</sub> model.
- [3] <a name="3"/>
  ["Datatypes as Lattices"](http://www.cs.ox.ac.uk/files/3287/PRG05.pdf)
  -Dana Scott (1976)
- [4] <a name="4"/>
  Pomagma began as a PhD [thesis](http://fritzo.org/thesis.pdf)
  and [codebase](http://github.com/fritzo/Johann).
- [5] <a name="5"/>
  See
  ["Predicativity"](http://math.stanford.edu/~feferman/papers/predicativity.pdf)
  or [other papers](http://math.stanford.edu/~feferman/papers.html)
  by Solomon Feferman.
