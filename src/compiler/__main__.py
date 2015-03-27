import os
import re
import contextlib
import multiprocessing
import parsable
import cProfile as profile
import pstats
from pomagma.compiler import compiler
from pomagma.compiler import cpp
from pomagma.compiler import extensional
from pomagma.compiler import parser
from pomagma.compiler.compiler import add_costs
from pomagma.compiler.compiler import compile_full
from pomagma.compiler.compiler import compile_given
from pomagma.compiler.compiler import get_events


SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SRC)


@parsable.command
def abstract(*args):
    '''
    Abstract variables from expression.
    Examples:
        abstract x 'APP x y'
        abstract x y z 'APP APP x z APP y z'
    '''
    args = map(parser.parse_string_to_expr, args)
    expression, vars = args[-1], args[:-1]
    for var in reversed(vars):
        expression = expression.abstract(var)
    print expression


@contextlib.contextmanager
def writer(outfile=None):
    if outfile is None:

        def write(line):
            print line
            print

        yield write
    else:
        with open(outfile, 'w') as f:

            def write(line):
                f.write(line)
                f.write('\n\n')

            yield write


def print_compiles(compiles):
    for cost, seq, strategy in compiles:
        print '# cost = {0}'.format(cost)
        print '# infer {0}'.format(seq)
        print re.sub(': ', '\n', repr(strategy))
        print


def measure_sequent(sequent):
    print '-' * 78
    print 'Compiling full search: {0}'.format(sequent)
    compiles = compile_full(sequent)
    print_compiles(compiles)
    full_cost = add_costs(c for (c, _, _) in compiles)

    incremental_cost = None
    for event in get_events(sequent):
        print 'Compiling incremental search given: {0}'.format(event)
        compiles = compile_given(sequent, event)
        print_compiles(compiles)
        if event.args:
            cost = add_costs(c for (c, _, _) in compiles)
            if incremental_cost:
                incremental_cost = add_costs([incremental_cost, cost])
            else:
                incremental_cost = cost
        else:
            pass  # event is only triggered once, so ignore cost

    print '# full cost =', full_cost, 'incremental cost =', incremental_cost


@parsable.command
def contrapositves(*filenames):
    '''
    Close rules under contrapositve
    '''
    sequents = []
    for filename in filenames:
        sequents += parser.parse_rules(filename)
    for sequent in sequents:
        print sequent.ascii()
        print
        for neg in sequent.contrapositives():
            print neg.ascii(indent=4)
            print


@parsable.command
def normalize(*filenames):
    '''
    Show normalized rule set derived from each rule
    '''
    sequents = []
    for filename in filenames:
        sequents += parser.parse_rules(filename)
    for sequent in sequents:
        print sequent.ascii()
        print
        for neg in sequent.contrapositives():
            print neg.ascii(indent=4)
            print


@parsable.command
def extract_tasks(infile, outfile=None):
    '''
    Extract tasks from rules, but do not compile to C++.
    '''
    with writer(outfile) as write:
        for sequent in parser.parse_rules(infile):
            write(sequent.ascii())
            for normal in sorted(compiler.normalize(sequent)):
                write(normal.ascii(indent=4))
            for event in sorted(compiler.get_events(sequent)):
                write('    Given: {}'.format(event))
                for normal in sorted(compiler.normalize_given(sequent, event)):
                    write(normal.ascii(indent=8))


def _extract_tasks((infile, outfile)):
    extract_tasks(infile, outfile)


@parsable.command
def batch_extract_tasks(*filenames):
    '''
    Extract tasks from infiles '*.rules', saving to '*.tasks'.
    '''
    pairs = []
    for infile in filenames:
        infile = os.path.abspath(infile)
        assert infile.endswith('.rules'), infile
        outfile = infile.replace('.rules', '.tasks')
        pairs.append((infile, outfile))
    multiprocessing.Pool().map(_extract_tasks, pairs)


@parsable.command
def measure(*filenames):
    '''
    Measure complexity of rules in files
    '''
    sequents = []
    for filename in filenames:
        sequents += parser.parse_rules(filename)
    for sequent in sequents:
        measure_sequent(sequent)


@parsable.command
def test_compile(*filenames):
    '''
    Compile rules -> C++
    '''
    for stem_rules in filenames:
        code = cpp.Code('// $filename', filename=stem_rules)
        assert stem_rules[-6:] == '.rules', stem_rules

        sequents = parser.parse_rules(stem_rules)
        for sequent in sequents:
            for cost, seq, strategy in compile_full(sequent):
                code.newline()
                code(
                    '''
                    // using $sequent
                    // infer $seq
                    // cost = $cost
                    ''',
                    cost=cost,
                    sequent=sequent,
                    seq=seq,
                )
                strategy.cpp(code)

            for event in get_events(sequent):
                for cost, seq, strategy in compile_given(sequent, event):
                    code.newline()
                    code(
                        '''
                        // given $event
                        // using $sequent
                        // infer $seq
                        // cost = $cost
                        ''',
                        event=event,
                        cost=cost,
                        sequent=sequent,
                        seq=seq,
                    )
                    strategy.cpp(code)

        print code


@parsable.command
def profile_compile(*filenames, **kwargs):
    '''
    Profile compiler on .
    Optional keyword arguments:
        loadfrom = None
        saveto = 'compiler.profile'
    '''
    loadfrom = kwargs.get('loadfrom')
    saveto = kwargs.get('saveto', 'compiler.profile')
    if loadfrom is None:
        command = 'compile({}, cpp_out="/dev/null")'.format(
            ', '.join(map('"{}"'.format, filenames)))
        print 'profiling {}'.format(command)
        profile.run(command, saveto)
        loadfrom = saveto
    stats = pstats.Stats(loadfrom)
    stats.strip_dirs()
    line_count = 50
    for sortby in ['time']:
        stats.sort_stats(sortby)
        stats.print_stats(line_count)


@parsable.command
def test_close_rules(infile, is_extensional=True):
    '''
    Compile extensionally some.rules -> some.derived.facts
    '''
    assert infile.endswith('.rules')
    rules = parser.parse_rules(infile)
    for rule in rules:
        print
        print '#', rule
        for fact in extensional.derive_facts(rule):
            print fact
            if is_extensional:
                extensional.validate(fact)


def relpath(string):
    is_path = '.' in string and '/' in string  # heuristic
    if is_path:
        return os.path.relpath(string, ROOT)
    else:
        return string


@parsable.command
def compile(*infiles, **kwargs):
    '''
    Compile rules -> C++.
    Optional keyword arguments:
        cpp_out=$POMAGMA_ROOT/src/surveyor/<STEM>.theory.cpp
        theory_out=$POMAGMA_ROOT/src/theory/<STEM>.compiled
        theory_out=FILENAME
        extensional=true
    '''
    stem = infiles[-1].split('.')[0]
    cpp_out = kwargs.get(
        'cpp_out',
        os.path.join(SRC, 'surveyor', '{0}.theory.cpp'.format(stem)))
    theory_out = kwargs.get(
        'theory_out',
        os.path.join(SRC, 'theory', '{0}.compiled'.format(stem)))
    parse_bool = {'true': True, 'false': False}
    is_extensional = parse_bool[kwargs.get('extensional', 'true').lower()]

    print '# writing', cpp_out
    argstring = ' '.join(
        [relpath(path) for path in infiles] +
        [
            '{0}={1}'.format(key, relpath(path))
            for key, path in kwargs.iteritems()
        ])

    rules = []
    facts = []
    for infile in infiles:
        suffix = infile.split('.')[-1]
        if suffix == 'rules':
            rules += parser.parse_rules(infile)
        elif suffix == 'facts':
            facts += parser.parse_facts(infile)
        else:
            raise TypeError('unknown file type: %s' % infile)
    if is_extensional:
        for rule in rules:
            facts += extensional.derive_facts(rule)

    code = cpp.Code()
    code('''
        // This file was auto generated by pomagma using:
        // python -m pomagma.compiler compile $argstring
        ''',
         argstring=argstring,
         ).newline()

    cpp.write_theory(code, rules, facts)

    with open(cpp_out, 'w') as f:
        f.write(str(code))

    with open(theory_out, 'w') as f:
        thisfile = relpath(os.path.abspath(__file__))
        f.write('# this file was generated by {0}'.format(thisfile))
        for fact in facts:
            assert fact.is_rel(), 'bad fact: %s' % fact
            f.write('\n')
            f.write(fact.polish)


if __name__ == '__main__':
    parsable.dispatch()
