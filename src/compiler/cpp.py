import re
from textwrap import dedent
from string import Template
from pomagma.compiler import compiler
from pomagma.compiler import signature
from pomagma.compiler.compiler import add_costs
from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import NotNegatable
from pomagma.compiler.expressions import try_negate_name
from pomagma.compiler.sequents import Sequent
from pomagma.compiler.util import inputs
from pomagma.compiler.util import methodof


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
def Iter_cpp(self, code, stack=None, poll=None):
    body = Code()
    if poll:
        body(poll)
    body(
        '''
        Ob $var = *iter;
        ''',
        var=self.var,
    )
    for var, expr in sorted(self.lets.iteritems()):
        body(
            '''
            Ob $var = $fun.find($args);
            ''',
            var=var,
            fun=expr.name,
            args=', '.join(map(str, expr.args)))
    self.body.cpp(body, stack=self.stack)
    sets = []
    iter_ = 'carrier.iter()'
    for test in self.tests:
        if test.arity == 'UnaryRelation':
            (arg,) = test.args
            iter_ = '%s.iter()' % test.name
            sets.append('%s.get_set()' % (test.name))
        elif test.arity == 'BinaryRelation':
            lhs, rhs = test.args
            assert lhs != rhs, lhs
            if self.var == lhs:
                iter_ = '%s.iter_rhs(%s)' % (test.name, rhs)
                sets.append('%s.get_Rx_set(%s)' % (test.name, rhs))
            else:
                iter_ = '%s.iter_lhs(%s)' % (test.name, lhs)
                sets.append('%s.get_Lx_set(%s)' % (test.name, lhs))
        else:
            raise ValueError('unknown relation {} of arity {}'.format(
                test.name,
                test.arity))
    for var, expr in sorted(self.lets.iteritems()):
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
def IterInvInjective_cpp(self, code, stack=None, poll=None):
    code(
        '''
        if (Ob $var __attribute__((unused)) = $fun.inverse_find($value))
        ''',
        var=self.var,
        fun=self.fun,
        value=self.value,
    )
    self.body.cpp(code, poll=poll)


@methodof(compiler.IterInvBinary, 'cpp')
def IterInvBinary_cpp(self, code, stack=None, poll=None):
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
def IterInvBinaryRange_cpp(self, code, stack=None, poll=None):
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
def Let_cpp(self, code, stack=None, poll=None):
    if stack and self in stack:
        self.body.cpp(code, stack=stack, poll=poll)
    else:
        code(
            '''
            if (Ob $var = $fun.find($args))
            ''',
            var=self.var,
            fun=self.expr.name,
            args=', '.join(map(str, self.expr.args)),
        )
        self.body.cpp(code, stack=stack, poll=poll)


@methodof(compiler.Test, 'cpp')
def Test_cpp(self, code, stack=None, poll=None):
    if stack and self in stack:
        self.body.cpp(code, stack=stack, poll=poll)
    else:
        args = [arg.name for arg in self.expr.args]
        if self.expr.name == 'EQUAL':
            expr = 'carrier.equal({0}, {1})'.format(*args)
        elif self.expr.arity == 'UnaryRelation':
            expr = '{0}.find({1})'.format(self.expr.name, *args)
        elif self.expr.arity == 'BinaryRelation':
            expr = '{0}.find({1}, {2})'.format(self.expr.name, *args)
        else:
            expr = '{0} == {1}.find({2})'.format(
                self.expr.var.name, self.expr.name, ', '.join(args))
        code(
            '''
            if ($expr)
            ''',
            expr=expr,
        )
        self.body.cpp(code, stack=stack, poll=poll)


@methodof(compiler.Ensure, 'cpp')
def Ensure_cpp(self, code, stack=None, poll=None):
    expr = self.expr
    args = [arg if arg.args else arg.var for arg in expr.args]
    if all(arg.is_var() for arg in args):
        code(
            '''
        ensure_$name($args);
        ''',
            name=expr.name.lower(),
            args=', '.join(map(str, args)),
        )
    else:
        assert self.expr.name == 'EQUAL', self.expr.name
        lhs, rhs = args
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
def write_signature(code, symbols):

    code(
        '''
        $bar
        // signature
        ''',
        bar=bar,
    ).newline()

    symbols = [
        (name, arity)
        for arity, names in symbols.iteritems()
        if (arity in signature.FUNCTION_ARITIES or
            arity in signature.RELATION_ARITIES)
        for name in names
        if name != 'EQUAL'
    ]
    symbols.sort(key=lambda (name, arity): (signature.arity_sort(arity), name))

    for name, arity in symbols:
        if name not in ['LESS', 'NLESS']:
            code(
                '''
                $Arity $NAME (carrier, schedule_$arity);
                ''',
                Arity=arity,
                arity=camel_to_underscore(arity),
                NAME=name,
                name=name.lower())
    code.newline()

    body = Code()
    body(
        '''
        signature.declare(carrier);
        ''',
    )
    for name, arity in symbols:
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
def write_merge_task(code, symbols):
    body = Code()
    body(
        '''
        const Ob dep = task.dep;
        const Ob rep = carrier.find(dep);
        POMAGMA_ASSERT(dep > rep, "ill-formed merge: " << dep << ", " << rep);
        bool invalid = NLESS.find(dep, rep) or NLESS.find(rep, dep);
        POMAGMA_ASSERT(not invalid, "invalid merge: " << dep << ", " << rep);
        std::vector<std::thread> threads;

        ''',
    )

    symbols = [
        (name, arity, signature.get_nargs(arity))
        for arity, names in symbols.iteritems()
        if arity != 'Variable'
        for name in names
        if name != 'EQUAL'
    ]
    symbols.sort(
        key=lambda (name, arity, argc): (
            -argc,
            signature.arity_sort(arity),
            name))

    for name, arity, argc in symbols:
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
def write_basic_ensurers(code, symbols):

    code(
        '''
        $bar
        // simple ensurers
        ''',
        bar=bar,
    ).newline()

    symbols = [
        (name, arity)
        for arity, names in symbols.iteritems()
        if arity in signature.RELATION_ARITIES
        for name in names
        if name not in ['EQUAL', 'LESS', 'NLESS']
    ]
    symbols.sort(key=lambda (name, arity): (signature.arity_sort(arity), name))

    def Ob(x):
        return 'Ob %s' % x

    for name, arity in symbols:
        argc = signature.get_nargs(arity)
        args = ['key'] if argc == 1 else ['lhs', 'rhs']
        code(
            '''
            inline void ensure_${name} ($typed_args)
            {
                $NAME.insert($args);
            }
            ''',
            name=name.lower(),
            NAME=name,
            args=', '.join(args),
            typed_args=', '.join(map(Ob, args)),
        ).newline()


@inputs(Code)
def write_compound_ensurers(code, symbols):

    code(
        '''
        $bar
        // compound ensurers
        ''',
        bar=bar,
    ).newline()

    symbols = [
        (name, arity)
        for arity, names in symbols.iteritems()
        if arity in signature.FUNCTION_ARITIES
        if signature.get_nargs(arity) > 0
        for name in names
    ]
    symbols.sort(key=lambda (name, arity): (signature.arity_sort(arity), name))

    def Ob(x):
        return 'Ob %s' % x

    for name1, arity1 in symbols:
        for name2, arity2 in symbols:
            if name1 > name2:
                continue

            argc1 = signature.get_nargs(arity1)
            argc2 = signature.get_nargs(arity2)
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
def write_assume_tasks(code, symbols):

    code(
        '''
        $bar
        // assume tasks
        ''',
        bar=bar,
    ).newline()

    symbols = [
        (name, arity)
        for arity, names in symbols.iteritems()
        if arity in signature.RELATION_ARITIES
        for name in names
    ]
    symbols.sort(key=lambda (name, arity): (signature.arity_sort(arity), name))

    cases = Code()

    prefix = 'if'
    for name, arity in symbols:
        argc = signature.get_nargs(arity)
        if argc == 1:
            cases(
                '''
                $prefix (type == "$NAME") {
                    Ob key = parser.parse_term();
                    parser.end();
                    ensure_${name}(key);
                ''',
                name=name.lower(),
                NAME=name,
                prefix=prefix,
            )
        elif argc == 2:
            cases(
                '''
                $prefix (type == "$NAME") {
                    Ob lhs = parser.parse_term();
                    Ob rhs = parser.parse_term();
                    parser.end();
                    ensure_${name}(lhs, rhs);
                ''',
                name=name.lower(),
                NAME=name,
                prefix=prefix,
            )
        else:
            raise ValueError('unhandled relation: {}'.format(name))
        prefix = '} else if'

    code(
        '''
        void execute (const AssumeTask & task)
        {
            POMAGMA_DEBUG("assume " << task.expression);

            InsertParser parser(signature);
            parser.begin(task.expression);
            std::string type = parser.parse_token();

            $cases
            } else {
                POMAGMA_ERROR("bad relation type: " << type);
            }
        }
        ''',
        cases=wrapindent(cases),
    ).newline()


@inputs(Code)
def write_full_tasks(code, sequents):

    full_tasks = []
    for sequent in sequents:
        for cost, seq, strategy in compiler.compile_full(sequent):
            full_tasks.append((cost, sequent, seq, strategy))
    full_tasks.sort()
    type_count = len(full_tasks)
    total_cost = add_costs(c for (c, _, _, _) in full_tasks)

    block_size = 64
    split = 'if (*iter / {} != block) {{ continue; }}'.format(block_size)
    min_split_cost = 1.5  # above which we split the outermost for loop
    unsplit_count = sum(
        1 for cost, _, _, _ in full_tasks
        if cost < min_split_cost
    )

    cases = Code()
    for i, (cost, sequent, seq, strategy) in enumerate(full_tasks):
        case = Code()
        strategy.cpp(case, poll=(split if cost >= min_split_cost else None))
        cases(
            '''
            case $index: { // cost = $cost
                // using $sequent
                // infer $seq
                $case
            } break;
            ''',
            index=i,
            cost=cost,
            case=wrapindent(case),
            sequent=sequent,
            seq=seq,
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
            // total cost = $cost
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
        cost=total_cost,
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
            strategies = sorted(compiler.compile_given(sequent, event))
            cost = add_costs(c for (c, _, _) in strategies)
            tasks = event_tasks.setdefault(name, [])
            tasks.append((cost, event, sequent, strategies))

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
        group_tasks.setdefault(groupname, {})[name] = sorted(tasks)

    group_tasks = sorted(group_tasks.iteritems())
    for groupname, group in group_tasks:
        group = sorted(group.iteritems())

        body = Code()

        for eventname, tasks in group:
            subbody = Code()
            subbody(
                '''
                // total cost = $cost
                ''',
                cost=add_costs(c for (c, _, _, _) in tasks),
            )
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

            for _, event, sequent, strategies in tasks:
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
                for cost, seq, strategy in strategies:
                    subsubbody.newline()
                    subsubbody('// infer $seq', seq=seq)
                    strategy.cpp(subsubbody)
                    subcost += cost
                if diagonal:
                    subbody(
                        '''
                        if (lhs == rhs) { // cost = $cost
                            // given $event
                            // using $sequent
                            $subsubbody
                        }
                        ''',
                        cost=cost,
                        subsubbody=wrapindent(subsubbody),
                        event=event,
                        sequent=sequent,
                    )
                else:
                    subbody(
                        '''
                        { // cost = $cost
                            // given $event
                            // using $sequent
                            $subsubbody
                        }
                        ''',
                        cost=cost,
                        subsubbody=wrapindent(subsubbody),
                        event=event,
                        sequent=sequent,
                    )

            if eventname in ['LESS', 'NLESS', '<variable>']:
                body(str(subbody)).newline()
            else:
                body(
                    '''
                    if (task.ptr == & $eventname) {
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

    nontrivial_arities = set(groupname for groupname, _ in group_tasks)
    nontrivial_arities.add('Equation')
    nontrivial_arities.add('BinaryRelation')
    for arity in signature.FUNCTION_ARITIES | signature.RELATION_ARITIES:
        if arity not in nontrivial_arities:
            code(
                '''
                void execute (const ${arity}Task &) {}
                ''',
                arity=arity,
            ).newline()


def get_symbols_used_in(sequents, exprs):
    symbols = {}
    tokens = set()
    for seq in sequents:
        assert isinstance(seq, Sequent), seq
        for expr in seq.antecedents | seq.succedents:
            tokens |= set(expr.polish.split())
    for expr in exprs:
        assert isinstance(expr, Expression), expr
        tokens |= set(expr.polish.split())
    for token in list(tokens):
        if signature.get_arity(token) in signature.RELATION_ARITIES:
            try:
                tokens.add(try_negate_name(token))
            except NotNegatable:
                pass
    valid_arities = signature.FUNCTION_ARITIES | signature.RELATION_ARITIES
    for c in tokens:
        arity = signature.get_arity(c)
        if arity in valid_arities:
            symbols.setdefault(signature.get_arity(c), []).append(c)
    for val in symbols.itervalues():
        val.sort()
    return symbols


@inputs(Code)
def write_theory(code, rules=None, facts=None):

    sequents = set(rules) if rules else set()
    facts = set(facts) if facts else set()
    symbols = get_symbols_used_in(sequents, facts)

    code(
        '''
        #include "theory.hpp"

        namespace pomagma
        {
        ''',
    ).newline()

    write_signature(code, symbols)
    write_merge_task(code, symbols)
    write_basic_ensurers(code, symbols)
    write_compound_ensurers(code, symbols)
    write_assume_tasks(code, symbols)
    write_full_tasks(code, sequents)
    write_event_tasks(code, sequents)

    code(
        '''
        } // namespace pomagma
        ''',
    )

    return code
