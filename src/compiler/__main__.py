import cProfile as profile
import contextlib
import glob
import multiprocessing
import os
import parsable
import pstats
import re
import simplejson as json
from pomagma.compiler import compiler
from pomagma.compiler import completion
from pomagma.compiler import extensional
from pomagma.compiler import frontend
from pomagma.compiler import parser
from pomagma.compiler import sequencer
from pomagma.compiler.compiler import compile_full
from pomagma.compiler.compiler import compile_given
from pomagma.compiler.compiler import get_events
from pomagma.compiler.plans import add_costs
from pomagma.compiler.sugar import desugar_expr
from pomagma.compiler.sugar import desugar_theory
from pomagma.compiler.util import find_theories

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SRC)


def up_to_date(infiles, outfiles):
    if not all(os.path.exists(f) for f in infiles + outfiles):
        return False
    infiles = glob.glob(os.path.join(SRC, 'compiler', '*.py')) + infiles
    intimes = map(os.path.getmtime, infiles)
    outtimes = map(os.path.getmtime, outfiles)
    return max(intimes) < min(outtimes)


def load_theory(filename):
    theory = parser.parse_theory(filename)
    theory = desugar_theory(theory)
    theory['rules'].sort()
    theory['facts'].sort()
    return theory


def json_load(filename):
    with open(filename) as f:
        return json.load(f)


def parse_bool(arg):
    return {'true': True, 'false': False}[arg.lower()]


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


@parsable.command
def desugar(*exprs):
    '''
    Convert lambda terms to combinators.
    Examples:
        desugar FUN x APP x y
        desugar FUN x FUN y FUN z APP APP x z APP y z
    '''
    for expr in map(parser.parse_string_to_expr, exprs):
        print expr
        print '  =', desugar_expr(expr)


@parsable.command
def complete(*facts):
    '''
    Complete a set of facts.
    '''
    facts = set(map(parser.parse_string_to_expr, facts))
    facts = completion.complete(facts)
    facts = sorted(facts)
    for fact in facts:
        print fact


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
    for cost, seq, plan in compiles:
        print '# cost = {0}'.format(cost)
        print '# infer {0}'.format(seq)
        print re.sub(': ', '\n', repr(plan))
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
    if not filenames:
        filenames = find_theories()
    sequents = []
    for filename in filenames:
        sequents += load_theory(filename)['rules']
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
    if not filenames:
        filenames = find_theories()
    sequents = []
    for filename in filenames:
        sequents += load_theory(filename)['rules']
    for sequent in sequents:
        print sequent.ascii()
        print
        for neg in sequent.contrapositives():
            print neg.ascii(indent=4)
            print


@parsable.command
def extract_tasks(infile, outfile=None):
    '''
    Extract tasks from facts and rules, but do not compile to C++.
    '''
    theory = load_theory(infile)
    with writer(outfile) as write:
        facts = theory['facts']
        for sequent in theory['rules']:
            facts += extensional.derive_facts(sequent)
        facts.sort()
        write('\n'.join(map(str, facts)))
        for sequent in theory['rules']:
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
def batch_extract_tasks(*filenames, **kwargs):
    '''
    Extract tasks from infiles '*.theory', saving to '*.tasks'.
    Options: parallel=true
    '''
    if not filenames:
        filenames = find_theories()
    pairs = []
    for infile in filenames:
        infile = os.path.abspath(infile)
        assert infile.endswith('.theory'), infile
        outfile = infile.replace('.theory', '.tasks')
        if not up_to_date([infile], [outfile]):
            pairs.append((infile, outfile))
    parallel = parse_bool(kwargs.get('parallel', 'true'))
    map_ = multiprocessing.Pool().map if parallel else map
    map_(_extract_tasks, pairs)


@parsable.command
def measure(*filenames):
    '''
    Measure complexity of rules in files
    '''
    if not filenames:
        filenames = find_theories()
    sequents = []
    for filename in filenames:
        sequents += load_theory(filename)['rules']
    for sequent in sequents:
        measure_sequent(sequent)


@parsable.command
def test_compile(*filenames):
    '''
    Compile rules -> C++
    '''
    if not filenames:
        filenames = find_theories()
    for stem_rules in filenames:
        programs = ['# {filename}'.format(filename=stem_rules)]
        assert stem_rules[-len('.theory'):] == '.theory', stem_rules

        sequents = load_theory(stem_rules)['rules']
        for sequent in sequents:
            for cost, seq, plan in compile_full(sequent):
                programs += [
                    '',
                    '# using {}'.format(sequent),
                    '# infer '.format(seq),
                    '# cost = '.format(cost),
                ]
                plan.program(programs)

            for event in get_events(sequent):
                for cost, seq, plan in compile_given(sequent, event):
                    programs += [
                        '',
                        '# given {}'.format(event),
                        '# using {}'.format(sequent),
                        '# infer {}'.format(seq),
                        '# cost {}'.format(cost),
                    ]
                    plan.program(programs)

        print '\n'.join(programs)


@parsable.command
def profile_tasks(*filenames, **kwargs):
    '''
    Profile task generation (first part of compiler chain).
    Optional keyword arguments:
        loadfrom = None
        saveto = 'tasks.pstats'
    '''
    if not filenames:
        filenames = find_theories()
    loadfrom = kwargs.get('loadfrom')
    saveto = kwargs.get('saveto', 'tasks.pstats')
    if loadfrom is None:
        command = 'batch_extract_tasks({}, parallel=false)'.format(
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
def profile_compile(*filenames, **kwargs):
    '''
    Profile full compiler chain (task generation + optimization).
    Optional keyword arguments:
        loadfrom = None
        saveto = 'compile.pstats'
    '''
    if not filenames:
        filenames = find_theories()
    loadfrom = kwargs.get('loadfrom')
    saveto = kwargs.get('saveto', 'compile.pstats')
    if loadfrom is None:
        command = 'compile({}, frontend_out="/dev/null")'.format(
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
    Compile extensionally some.theory -> some.derived.facts
    '''
    assert infile.endswith('.theory')
    rules = load_theory(infile)['rules']
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
        symbols_out=$POMAGMA_ROOT/src/theory/<STEM>.symbols
        facts_out=$POMAGMA_ROOT/src/theory/<STEM>.facts
        programs_out=$POMAGMA_ROOT/src/theory/<STEM>.programs
        optimized_out=$POMAGMA_ROOT/src/theory/<STEM>.optimized.programs
        extensional=true
    '''
    stem = infiles[-1].split('.')[0]
    symbols_out = kwargs.get(
        'symbols_out',
        os.path.join(SRC, 'theory', '{0}.symbols'.format(stem)))
    facts_out = kwargs.get(
        'facts_out',
        os.path.join(SRC, 'theory', '{0}.facts'.format(stem)))
    programs_out = kwargs.get(
        'programs_out',
        os.path.join(SRC, 'theory', '{0}.programs'.format(stem)))
    optimized_out = kwargs.get(
        'optimized_out',
        os.path.join(SRC, 'theory', '{0}.optimized.programs'.format(stem)))
    is_extensional = parse_bool(kwargs.get('extensional', 'true'))

    argstring = ' '.join(
        [relpath(path) for path in infiles] +
        [
            '{0}={1}'.format(key, relpath(path))
            for key, path in kwargs.iteritems()
        ])
    header = (
        '# This file was auto generated by pomagma using:\n'
        '# python -m pomagma.compiler compile {0}'.format(argstring)
    )

    rules = []
    facts = []
    for infile in infiles:
        theory = load_theory(infile)
        rules += theory['rules']
        facts += theory['facts']
    if is_extensional:
        for rule in rules:
            facts += extensional.derive_facts(rule)
    rules.sort()
    facts.sort()

    symbols = frontend.write_symbols(rules, facts)
    with open(symbols_out, 'w') as f:
        print '# writing', symbols_out
        f.write(header)
        for arity, name in symbols:
            f.write('\n{} {}'.format(arity, name))

    with open(facts_out, 'w') as f:
        print '# writing', facts_out
        f.write(header)
        for fact in facts:
            assert fact.is_rel(), 'bad fact: %s' % fact
            f.write('\n')
            f.write(fact.polish)

    programs = frontend.write_programs(rules)
    with open(programs_out, 'w') as f:
        print '# writing', programs_out
        f.write(header)
        for line in programs:
            f.write('\n')
            f.write(line)

    lines = sequencer.load_lines(programs_out)
    optimized = sequencer.optimize(lines)
    with open(optimized_out, 'w') as f:
        print '# writing', optimized_out
        f.write(header)
        for line in optimized:
            f.write('\n')
            f.write(line)


def _compile(param):
    compile(*param['args'], **param['kwargs'])


@parsable.command
def batch_compile(parallel=True):
    '''
    Compile all theories in parallel.
    '''
    params = []
    theories_json = os.path.join(SRC, 'theory', 'theories.json')
    theories = json_load(theories_json)
    for name, spec in theories.iteritems():
        infiles = sorted(
            os.path.join(SRC, 'theory', '{}.theory'.format(t))
            for t in spec['theories']
        )
        symbols_out = os.path.join(SRC, 'theory', '{}.symbols'.format(name))
        facts_out = os.path.join(SRC, 'theory', '{}.facts'.format(name))
        programs_out = os.path.join(SRC, 'theory', '{}.programs'.format(name))
        optimized_out = os.path.join(
            SRC,
            'theory',
            '{}.optimized.programs'.format(name))
        outfiles = [symbols_out, facts_out, programs_out]
        if not up_to_date(infiles + [theories_json], outfiles):
            params.append({
                'args': infiles,
                'kwargs': {
                    'symbols_out': symbols_out,
                    'facts_out': facts_out,
                    'programs_out': programs_out,
                    'optimized_out': optimized_out,
                    'extensional': str(spec.get('extensional', True)),
                }})
    map_ = multiprocessing.Pool().map if parallel else map
    map_(_compile, params)


if __name__ == '__main__':
    parsable.dispatch()
