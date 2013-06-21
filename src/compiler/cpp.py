import re
from textwrap import dedent
from string import Template
from pomagma.compiler.util import inputs, methodof, log_sum_exp
from pomagma.compiler.expressions import Expression
from pomagma.compiler.sequents import Sequent
from pomagma.compiler import signature
from pomagma.compiler import compiler


def camel_to_underscore(camel):
    return re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel).lower()


def sub(template, **kwds):
    return Template(dedent(template)).substitute(kwds)


def wrapindent(text, indent='    '):
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r'(\n+)', r'\1' + indent, text.strip())


def join(*lines):
    return '\n'.join(lines)


bar = '//' + '-' * 76


class Code:

    def __init__(self, text='', **kwargs):
        text = dedent(text).strip()
        if kwargs:
            text = Template(text).substitute(kwargs)
        self.text = text

    def newline(self):
        self.text += '\n'
        return self

    def __call__(self, text, **kwargs):
        text = dedent(text).strip()
        if kwargs:
            text = Template(text).substitute(kwargs)
        if self.text:
            self.newline()
        self.text += text
        return self

    def __str__(self):
        return self.text

    def __repr__(self):
        return 'Code(%s)' % self.text


@methodof(compiler.Iter, 'cpp')
def Iter_cpp(self, code, poll=None):
    body = Code()
    if poll:
        body(poll)
    body(
        '''
        Ob $var = *iter;
        ''',
        var=self.var,
    )
    for var, expr in self.lets.iteritems():
        body(
            '''
            Ob $var = $fun.find($args);
            ''',
            var=var,
            fun=expr.name,
            args=', '.join(map(str, expr.args)))
    self.body.cpp(body)
    sets = []
    iter_ = 'carrier.iter()'
    for test in self.tests:
        assert test.name in ['LESS', 'NLESS'], test.name
        lhs, rhs = test.args
        assert lhs != rhs, lhs
        if self.var == lhs:
            iter_ = '%s.iter_rhs(%s)' % (test.name, rhs)
            sets.append('%s.get_Rx_set(%s)' % (test.name, rhs))
        else:
            iter_ = '%s.iter_lhs(%s)' % (test.name, lhs)
            sets.append('%s.get_Lx_set(%s)' % (test.name, lhs))
    for expr in self.lets.itervalues():
        assert self.var in expr.args,\
            '{} not in {}'.format(self.var, expr.args)
        if len(expr.args) == 1:
            iter_ = '%s.iter()' % expr.name
            sets.append('%s.get_set()' % expr.name)
        else:
            lhs, rhs = expr.args
            assert lhs != rhs, lhs
            if self.var == lhs:
                iter_ = '%s.iter_rhs(%s)' % (expr.name, rhs)
                sets.append('%s.get_Rx_set(%s)' % (expr.name, rhs))
            else:
                iter_ = '%s.iter_lhs(%s)' % (expr.name, lhs)
                sets.append('%s.get_Lx_set(%s)' % (expr.name, lhs))
    if len(sets) > 1:
        iter_ = '{}.iter_insn({})'.format(sets[0], ', '.join(sets[1:]))
    code(
        '''
        for (auto iter = $iter; iter.ok(); iter.next()) {
            $body
        }
        ''',
        iter=iter_,
        body=wrapindent(body),
    )


# TODO injective function inverse need not be iterated
@methodof(compiler.IterInvInjective, 'cpp')
def IterInvInjective_cpp(self, code, poll=None):
    body = Code()
    self.body.cpp(body, poll=poll)
    code(
        '''
        if (Ob $var __attribute__((unused)) = $fun.inverse_find($value)) {
            $body
        }
        ''',
        var=self.var,
        fun=self.fun,
        value=self.value,
        body=wrapindent(body),
    )


@methodof(compiler.IterInvBinary, 'cpp')
def IterInvBinary_cpp(self, code, poll=None):
    body = Code()
    if poll:
        body(poll)
    if self.var1 == self.var2:
        body(
            '''
            Ob $var1 __attribute__((unused)) = iter.lhs();
            ''',
            var1=self.var1,
        )
    else:
        body(
            '''
            Ob $var1 __attribute__((unused)) = iter.lhs();
            Ob $var2 __attribute__((unused)) = iter.rhs();
            ''',
            var1=self.var1,
            var2=self.var2,
        )
    self.body.cpp(body)
    code(
        '''
        for (auto iter = $fun.iter_val($value); iter.ok(); iter.next()) {
            $body
        }
        ''',
        fun=self.fun,
        value=self.value,
        body=wrapindent(body),
    )


@methodof(compiler.IterInvBinaryRange, 'cpp')
def IterInvBinaryRange_cpp(self, code, poll=None):
    body = Code()
    if poll:
        body(poll)
    body(
        '''
        Ob $var __attribute__((unused)) = *iter;
        ''',
        var=self.var2 if self.lhs_fixed else self.var1,
    )
    self.body.cpp(body)
    iter_ = Code()
    iter_(
        '''
        $fun.iter_val_$parity($value, $var)
        ''',
        fun=self.fun,
        value=self.value,
        parity=('lhs' if self.lhs_fixed else 'rhs'),
        var=(self.var1 if self.lhs_fixed else self.var2),
    )
    code(
        '''
        for (auto iter = $iter_; iter.ok(); iter.next()) {
            $body
        }
        ''',
        iter_=iter_,
        body=wrapindent(body),
    )


@methodof(compiler.Let, 'cpp')
def Let_cpp(self, code, poll=None):
    body = Code()
    self.body.cpp(body, poll=poll)
    code(
        '''
        if (Ob $var = $fun.find($args)) {
            $body
        }
        ''',
        var=self.var,
        fun=self.expr.name,
        args=', '.join(map(str, self.expr.args)),
        body=wrapindent(body),
    )


@methodof(compiler.Test, 'cpp')
def Test_cpp(self, code, poll=None):
    body = Code()
    self.body.cpp(body, poll=poll)
    args = [arg.name for arg in self.expr.args]
    if self.expr.name == 'EQUAL':
        expr = 'carrier.equal({0}, {1})'.format(*args)
    elif self.expr.name in ['LESS', 'NLESS']:
        expr = '{0}.find({1}, {2})'.format(self.expr.name, *args)
    else:
        expr = '{0} == {1}.find({2})'.format(
            self.expr.var.name, self.expr.name, ', '.join(args))
    code(
        '''
        if ($expr) {
            $body
        }
        ''',
        expr=expr,
        body=wrapindent(body),
    )


@methodof(compiler.Ensure, 'cpp')
def Ensure_cpp(self, code, poll=None):
    expr = self.expr
    assert len(expr.args) == 2, expr.args
    args = [arg if arg.args else arg.var for arg in expr.args]
    lhs, rhs = args
    if lhs.is_var() and rhs.is_var():
        code(
            '''
        ensure_$name($args);
        ''',
            name=expr.name.lower(),
            args=', '.join(map(str, args)),
        )
    else:
        assert self.expr.name == 'EQUAL', self.expr.name
        if lhs.is_var():
            code(
                '''
                $name.insert($arg1, $arg2);
                ''',
                name=rhs.name,
                arg1=', '.join(map(str, rhs.args)),
                arg2=lhs,
            )
        elif rhs.is_var():
            code(
                '''
                $name.insert($arg1, $arg2);
                ''',
                name=lhs.name,
                arg1=', '.join(map(str, lhs.args)),
                arg2=rhs,
            )
        else:
            if rhs.name < lhs.name:
                lhs, rhs = rhs, lhs
            code(
                '''
                ensure_${name1}_${name2}($args);
                ''',
                name1=lhs.name.lower(),
                name2=rhs.name.lower(),
                args=', '.join(map(str, lhs.args + rhs.args)),
            )


@inputs(Code)
def write_signature(code, functions):

    code(
        '''
        $bar
        // signature
        ''',
        bar=bar,
    ).newline()

    for arity, names in functions.iteritems():
        for name in names:
            code(
                '''
                $Arity $NAME (carrier, schedule_$arity);
                ''',
                Arity=arity,
                arity=camel_to_underscore(arity),
                NAME=name,
                name=name.lower())
        if names:
            code.newline()

    body = Code()
    body(
        '''
        signature.declare(carrier);
        signature.declare("LESS", LESS);
        signature.declare("NLESS", NLESS);
        ''',
    )
    for arity, names in functions.iteritems():
        for name in names:
            body(
                '''
                signature.declare("$NAME", $NAME);
                ''',
                NAME=name)
    code(
        '''
        void declare_signature ()
        {
            $body
        }
        ''',
        body=wrapindent(body),
    ).newline()


@inputs(Code)
def write_merge_task(code, functions):
    body = Code()
    body(
        '''
        const Ob dep = task.dep;
        const Ob rep = carrier.find(dep);
        POMAGMA_ASSERT(dep > rep, "ill-formed merge: " << dep << ", " << rep);
        bool invalid = NLESS.find(dep, rep) or NLESS.find(rep, dep);
        POMAGMA_ASSERT(not invalid, "invalid merge: " << dep << ", " << rep);

        std::vector<std::thread> threads;
        threads.push_back(std::thread(
            &BinaryRelation::unsafe_merge,
            &LESS,
            dep));
        threads.push_back(std::thread(
            &BinaryRelation::unsafe_merge,
            &NLESS,
            dep));
        ''',
    )

    functions = [
        (name, arity, signature.get_nargs(arity))
        for arity, funs in functions.iteritems()
        for name in funs
    ]
    functions.sort(key=lambda (name, arity, argc): -argc)

    for name, arity, argc in functions:
        if argc <= 1:
            body('$name.unsafe_merge(dep);', name=name)
        else:
            body(
                '''
                threads.push_back(std::thread(
                    &$arity::unsafe_merge,
                    &$name,
                    dep));
                ''',
                name=name,
                arity=arity,
            )
    body.newline()

    body(
        '''
        for (auto & thread : threads) { thread.join(); }
        carrier.unsafe_remove(dep);
        '''
    )

    code(
        '''
        void execute (const MergeTask & task)
        {
            $body
        }
        ''',
        body=wrapindent(body),
    ).newline()


@inputs(Code)
def write_ensurers(code, functions):

    code(
        '''
        $bar
        // compound ensurers
        ''',
        bar=bar,
    ).newline()

    functions = [(name, signature.get_nargs(arity))
                 for arity, funs in functions.iteritems()
                 if signature.get_nargs(arity) > 0
                 for name in funs]

    def Ob(x):
        return 'Ob %s' % x

    for name1, argc1 in functions:
        for name2, argc2 in functions:
            if name1 > name2:
                continue

            vars1 = ['key1'] if argc1 == 1 else ['lhs1', 'rhs1']
            vars2 = ['key2'] if argc2 == 1 else ['lhs2', 'rhs2']
            code(
                '''
                inline void ensure_${name1}_${name2} (
                    $typed_args1,
                    $typed_args2)
                {
                    if (Ob val1 = $NAME1.find($args1)) {
                        $NAME2.insert($args2, val1);
                    } else {
                        if (Ob val2 = $NAME2.find($args2)) {
                            $NAME1.insert($args1, val2);
                        }
                    }
                }
                ''',
                name1=name1.lower(),
                name2=name2.lower(),
                NAME1=name1,
                NAME2=name2,
                args1=', '.join(vars1),
                args2=', '.join(vars2),
                typed_args1=', '.join(map(Ob, vars1)),
                typed_args2=', '.join(map(Ob, vars2)),
            ).newline()


@inputs(Code)
def write_full_tasks(code, sequents):

    full_tasks = []
    for sequent in sequents:
        full_tasks += compiler.compile_full(sequent)
    full_tasks.sort(key=(lambda (cost, _): cost))
    type_count = len(full_tasks)

    block_size = 64
    split = 'if (*iter / {} != block) {{ continue; }}'.format(block_size)
    min_split_cost = 1.5  # above which we split the outermost for loop
    unsplit_count = sum(1 for cost, _ in full_tasks if cost < min_split_cost)

    cases = Code()
    for i, (cost, strategy) in enumerate(full_tasks):
        case = Code()
        strategy.cpp(case, split if cost >= min_split_cost else None)
        cases(
            '''
            case $index: { // cost = $cost
                $case
            } break;
            ''',
            index=i,
            cost=cost,
            case=wrapindent(case),
        ).newline()

    code(
        '''
        $bar
        // cleanup tasks

        const size_t g_cleanup_type_count = $type_count;
        const size_t g_cleanup_block_count =
            carrier.item_dim() / $block_size + 1;
        const size_t g_cleanup_task_count =
            $unsplit_count +
            ($type_count - $unsplit_count) * g_cleanup_block_count;
        std::atomic<unsigned long> g_cleanup_type(0);
        std::atomic<unsigned long> g_cleanup_remaining(0);
        CleanupProfiler g_cleanup_profiler(g_cleanup_type_count);

        inline unsigned long next_cleanup_type (const unsigned long & type)
        {
            unsigned long next = type < $unsplit_count * g_cleanup_block_count
                                      ? type + g_cleanup_block_count
                                      : type + 1;
            return next % (g_cleanup_type_count * g_cleanup_block_count);
        }

        void cleanup_tasks_push_all()
        {
            g_cleanup_remaining.store(g_cleanup_task_count);
        }

        bool cleanup_tasks_try_pop (CleanupTask & task)
        {
            unsigned long remaining = 1;
            while (not g_cleanup_remaining.compare_exchange_weak(
                remaining, remaining - 1))
            {
                if (remaining == 0) {
                    return false;
                }
            }

            // is this absolutely correct?

            unsigned long type = 0;
            while (not g_cleanup_type.compare_exchange_weak(
                type, next_cleanup_type(type)))
            {
            }

            task.type = type;
            return true;
        }

        void execute (const CleanupTask & task)
        {
            const unsigned long type = task.type / g_cleanup_block_count;
            const unsigned long block = task.type % g_cleanup_block_count;
            POMAGMA_DEBUG(
                "executing cleanup task"
                " type " << (1 + type) << "/" << g_cleanup_type_count <<
                " block " << (1 + block) << "/" << g_cleanup_block_count);
            CleanupProfiler::Block profiler_block(type);

            switch (type) {

                $cases

                default: POMAGMA_ERROR("bad cleanup type " << type);
            }
        }
        ''',
        bar=bar,
        type_count=type_count,
        unsplit_count=unsplit_count,
        block_size=block_size,
        cases=wrapindent(cases, '        '),
    ).newline()


@inputs(Code)
def write_event_tasks(code, sequents):

    code(
        '''
        $bar
        // event tasks
        ''',
        bar=bar,
    ).newline()

    event_tasks = {}
    for sequent in sequents:
        for event in compiler.get_events(sequent):
            name = '<variable>' if event.is_var() else event.name
            tasks = event_tasks.setdefault(name, [])
            strategies = compiler.compile_given(sequent, event)
            strategies.sort(key=lambda (cost, _): cost)
            costs = [cost for cost, _ in strategies]
            cost = log_sum_exp(*costs)
            tasks.append((event, cost, strategies))

    def get_group(name):
        special = {
            'LESS': 'PositiveOrder',
            'NLESS': 'NegativeOrder',
            '<variable>': 'Exists',
        }
        return special.get(name, signature.get_arity(name))

    group_tasks = {}
    for name, tasks in event_tasks.iteritems():
        groupname = get_group(name)
        group_tasks.setdefault(groupname, {})[name] = tasks

    # TODO sort groups
    # event_tasks = event_tasks.items()
    # event_tasks.sort(key=lambda (name, tasks): (len(tasks), len(name), name))

    group_tasks = list(group_tasks.iteritems())
    group_tasks.sort()

    for groupname, group in group_tasks:
        group = list(group.iteritems())
        group.sort()

        body = Code()

        for eventname, tasks in group:
            subbody = Code()
            nargs = signature.get_nargs(signature.get_arity(group[0][0]))
            args = [[], ['arg'], ['lhs', 'rhs']][nargs]
            for arg in args:
                subbody('const Ob $arg = task.$arg;', arg=arg)
            if signature.is_fun(eventname):
                subbody(
                    '''
                    const Ob val = $eventname.find($args);
                    ''',
                    eventname=eventname,
                    args=', '.join(args))

            for event, _, strategies in tasks:
                subsubbody = Code()
                diagonal = (nargs == 2 and event.args[0] == event.args[1])
                if diagonal:
                    subsubbody(
                        '''
                        const Ob $local __attribute__((unused)) = $arg;
                        ''',
                        local=event.args[0],
                        arg=args[0],
                    )
                else:
                    for local, arg in zip(event.args, args):
                        subsubbody(
                            '''
                            const Ob $local __attribute__((unused)) = $arg;
                            ''',
                            local=local,
                            arg=arg,
                        )
                if event.is_fun():
                    subsubbody('const Ob $arg = val;', arg=event.var.name)
                elif event.is_var():
                    subsubbody('const Ob $arg = task.ob;', arg=event.name)
                subcost = 0
                for cost, strategy in strategies:
                    subsubbody.newline()
                    strategy.cpp(subsubbody)
                    subcost += cost
                if diagonal:
                    subbody(
                        '''
                        if (lhs == rhs) { // cost = $cost
                            $subsubbody
                        }
                        ''',
                        cost=cost,
                        subsubbody=wrapindent(subsubbody),
                    )
                else:
                    subbody(
                        '''
                        { // cost = $cost
                            $subsubbody
                        }
                        ''',
                        cost=cost,
                        subsubbody=wrapindent(subsubbody),
                    )

            if eventname in ['LESS', 'NLESS', '<variable>']:
                body(str(subbody)).newline()
            else:
                body(
                    '''
                if (task.fun == & $eventname) {
                    $subbody
                }
                ''',
                    eventname=eventname,
                    subbody=wrapindent(subbody),
                ).newline()

        code(
            '''
            void execute (const ${groupname}Task & task)
            {
                $body
            }
            ''',
            groupname=groupname,
            body=wrapindent(body),
        ).newline()

    nontrivial_arities = [groupname for groupname, _ in group_tasks]
    for arity in signature.FUNCTION_ARITIES:
        if arity not in nontrivial_arities:
            code(
                '''
                void execute (const ${arity}Task &) {}
                ''',
                arity=arity,
            ).newline()


def get_functions_used_in(sequents, exprs):
    functions = dict((arity, []) for arity in signature.FUNCTION_ARITIES)
    symbols = set()
    for seq in sequents:
        assert isinstance(seq, Sequent), seq
        for expr in seq.antecedents | seq.succedents:
            symbols |= set(expr.polish.split())
    for expr in exprs:
        assert isinstance(expr, Expression), expr
        symbols |= set(expr.polish.split())
    for c in symbols:
        if signature.is_fun(c):
            functions[signature.get_arity(c)].append(c)
    for val in functions.itervalues():
        val.sort()
    return functions


@inputs(Code)
def write_theory(code, rules=None, facts=None):

    sequents = set(rules) if rules else set()
    facts = set(facts) if facts else set()
    functions = get_functions_used_in(sequents, facts)

    code(
        '''
        #include "theory.hpp"

        namespace pomagma
        {
        ''',
    ).newline()

    write_signature(code, functions)
    write_merge_task(code, functions)
    write_ensurers(code, functions)
    write_full_tasks(code, sequents)
    write_event_tasks(code, sequents)

    code(
        '''
        } // namespace pomagma
        ''',
    )

    return code
