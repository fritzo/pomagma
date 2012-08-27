import re
from textwrap import dedent
from string import Template
from pomagma.util import TODO, inputs, union, methodof
from pomagma.sequents import Sequent
from pomagma import signature
from pomagma import compiler


def sub(template, **kwds):
    return Template(dedent(template)).substitute(kwds)


def wrapindent(text, indent='    '):
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r'(\n+)', r'\1' + indent, text)


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


@methodof(compiler.Iter)
def cpp(self, code):
    body = Code('''
        oid_t $var = *iter;
        ''',
        var = self.var,
        )
    for var, expr in self.lets.iteritems():
        body('''
            oid_t $var = $fun.find($args);
            ''',
            var = var,
            fun = expr.name,
            args = ', '.join(map(str, expr.args)))
    self.body.cpp(body)
    sets = []
    for test in self.tests:
        sets.append('TODO %s' % test)
    for var, expr in self.lets.iteritems():
        sets.append('TODO %s' % var)
    if len(sets) == 0:
        code('''
            const dense_set & set = carrier.support();
            ''')
    elif len(sets) == 1:
        code('''
            dense_set set(carrier.item_dim(), $one_set);
            ''',
            one_set = iter(sets).next())
    else:
        code('''
            dense_set set(carrier.item_dim());
            set.set_union($sets);
            ''',
            sets = ', '.join(sets),
            )
    code('''
        for (dense_set::iterator iter(set); iter.ok(); iter.next()) {',
            $body
        }
        ''',
        body=wrapindent(body),
        )


@methodof(compiler.IterInvInjective)
def cpp(self, code):
    body = Code('''
        oid_t $var = iter.arg();
        ''', var=self.var)
    body += self.body.cpp_lines()
    body = ['    ' + line for line in body]
    code('''
        for (InjectiveFunction::inverse_iterator iter($value);
            iter.ok(); iter.next())
        {
            $body
        }
        ''',
        value = self.value,
        body = wrapindent(body),
        )


@methodof(compiler.IterInvBinary)
def cpp(self, code):
    body = Code('''
        oid_t $var1 = iter.lhs();
        oid_t $var2 = iter.rhs();
        ''',
        var1 = self.var1,
        var2 = self.var2,
        )
    self.body.cpp(body)
    code('''
        for (BinaryFunction::inverse_iterator iter($value);
            iter.ok(); iter.next())
        {
            $body
        }
        ''',
        value = self.value,
        body = wrapindent(body),
        )


@methodof(compiler.IterInvBinaryRange)
def cpp(self, code):
    body = Code('''
        oid_t $var = iter.$moving();
        ''',
        var = self.var2 if self.lhs_fixed else self.var1,
        moving = 'rhs' if self.lhs_fixed else 'lhs',
        )
    self.body.cpp(body)
    code('''
        for (BinaryFunction::inv_range_iterator iter($var1, $var2);
            iter.ok(); iter.next())
        {
            $body
        }
        ''',
        var1 = self.value,
        var2 = self.var2 if self.lhs_fixed else self.var1,
        body = wrapindent(body),
        )


@methodof(compiler.Let)
def cpp(self, code):
    body = Code()
    self.body.cpp(body)
    if self.expr.args:
        expr = str(self.expr)
    else:
        expr = 'signature::%s()' % self.expr
    code('''
        if (oid_t $var = $expr) {
            $body
        }
        ''',
        var = self.var,
        expr = expr,
        body = wrapindent(body),
        )


@methodof(compiler.Test)
def cpp(self, code):
    body = Code()
    self.body.cpp(code)
    code('''
        if ($expr) {
            $body
        }
        ''',
        expr = self.expr,
        body = wrapindent(body),
        )


@methodof(compiler.Ensure)
def cpp(self, code):
    expr = self.expr
    assert len(expr.args) == 2
    lhs, rhs = expr.args
    if lhs.is_var() and rhs.is_var():
        code('''
            ensure_${name}($args);
            ''',
            name = expr.name.lower(),
            args = ', '.join(map(str, expr.args)),
            )
    else:
        assert self.expr.name == 'EQUAL'
        if lhs.is_var():
            code('''
                ensure_${name}($arg1, $arg2);
                ''',
                name = rhs.name.lower(),
                arg1 = ', '.join(map(str, rhs.args)),
                arg2 = lhs,
                )
        elif rhs.is_var():
            code('''
                ensure_${name}($arg1, $arg2);
                ''',
                name = lhs.name.lower(),
                arg1 = ', '.join(map(str, lhs.args)),
                arg2 = rhs,
                )
        else:
            if rhs.name < lhs.name:
                lhs, rhs = rhs, lhs
            code('''
                ensure_${name1}_${name2}($args);
                ''',
                name1 = lhs.name.lower(),
                name2 = rhs.name.lower(),
                args = ', '.join(map(str, lhs.args + rhs.args)),
                )



@inputs(Code)
def write_signature(code, functions):

    funs = Code()
    for arity, names in functions.iteritems():
        for name in names:
            funs('''
                $arity $name(carrier);
                ''',
                arity = arity,
                name = name)
        if names:
            funs.newline()

    code('''
        $bar
        // signature

        namespace signature {

        Carrier carrier;
        const dense_set support(carrier.support(), yes_copy_construct);
        inline size_t item_dim () { return support.item_dim(); }

        BinaryRelation LESS(carrier);
        BinaryRelation NLESS(carrier);
        
        $funs
        } // namespace signature

        using namespace signature;
        ''',
        bar = bar,
        funs = funs,
        ).newline()

def write_ensurers(code, functions):

    code('''
        $bar
        // ensurers

        inline void ensure_equal (oid_t lhs, oid_t rhs)
        {
            if (lhs != rhs) {
                oid_t dep = lhs < rhs ? lhs : rhs;
                oid_t rep = lhs < rhs ? rhs : lhs;
                carrier.merge(dep, rep);
                schedule(MergeTask(dep));
            }
        }

        // TODO most uses of this can be vectorized
        // TODO use .contains_Lx/.contains_Rx based on iterator direction
        inline void ensure_less (oid_t lhs, oid_t rhs)
        {
            // TODO do this more atomically
            if (not LESS(lhs, rhs)) {
                LESS.insert(lhs, rhs);
                schedule(PositiveOrderTask(lhs, rhs));
            }
        }

        // TODO most uses of this can be vectorized
        // TODO use .contains_Lx/.contains_Rx based on iterator direction
        inline void ensure_nless (oid_t lhs, oid_t rhs)
        {
            // TODO do this more atomically
            if (not NLESS(lhs, rhs)) {
                NLESS.insert(lhs, rhs);
                schedule(NegativeOrderTask(lhs, rhs));
            }
        }
        ''',
        bar = bar,
        ).newline()

    functions = [(name, arity, signature.get_nargs(arity))
                 for arity, funs in functions.iteritems()
                 if signature.get_nargs(arity) > 0
                 for name in funs]

    def oid_t(x):
        return 'oid_t %s' % x

    for name, arity, argc in functions:
        vars_ = ['key'] if argc == 1 else ['lhs', 'rhs']
        code('''
            inline void ensure_${name} ($typed_args, oid_t val)
            {
                if (oid_t old_val = $NAME($args)) {
                    ensure_equal(old_val, val);
                } else {
                    $NAME.insert($args, val);
                    schedule(${arity}Task($NAME, $args));
                }
            }
            ''',
            name=name.lower(),
            NAME=name,
            args=', '.join(vars_),
            typed_args=', '.join(map(oid_t, vars_)),
            arity=arity,
            ).newline()

    for name1, arity1, argc1 in functions:
        for name2, arity2, argc2 in functions:
            if name2 > name1:
                continue

            vars1 = ['key1'] if argc1 == 1 else ['lhs1', 'rhs1']
            vars2 = ['key2'] if argc2 == 1 else ['lhs2', 'rhs2']
            code('''
                inline void ensure_${name1}_${name2} (
                    $typed_args1,
                    $typed_args2)
                {
                    if (oid_t val1 = $NAME1.find($args1)) {
                        ensure_${name2}($args2, val1);
                    } else {
                        if (oid_t val2 = $NAME2.find($args2)) {
                            $NAME1.insert($args1, val2);
                            schedule(${arity1}Task($NAME1, $args1));
                        }
                    }
                }
                ''',
                name1 = name1.lower(),
                name2 = name2.lower(),
                NAME1 = name1,
                NAME2 = name2,
                args1 = ', '.join(vars1),
                args2 = ', '.join(vars2),
                typed_args1 = ', '.join(map(oid_t, vars1)),
                typed_args2 = ', '.join(map(oid_t, vars2)),
                arity1 = arity,
                arity2 = arity2,
                ).newline()

def write_full_tasks(code, sequents):

    full_tasks = []
    for sequent in sequents:
        full_tasks += compiler.compile_full(sequent)
    full_tasks.sort(key=(lambda (cost, _): cost))
    type_count = len(full_tasks)

    cases = Code()
    for i, (cost, strategy) in enumerate(full_tasks):
        case = Code()
        strategy.cpp(case)
        cases('''
            case $index: { // cost = $cost
                $case
            } break;
            ''',
            index = i,
            cost = cost,
            case = wrapindent(case),
            ).newline()

    code('''
        $bar
        // full tasks

        const size_t g_type_count = $type_count;
        std::vector<std::atomic_flag> g_clean_state(g_type_count, true);

        void set_state_dirty ()
        {
            for (auto & state : g_clean_state) {
                state.clear();
            }
        }

        void execute (const CleanupTask & task)
        {
            // HACK
            // TODO find a better cleanup scheduling policy
            size_t next_type = (task.type + 1) % g_type_count;
            if (task.type >= g_type_count) {
                schedule(CleanupTask(0));
            }
            if (not g_clean_state[task.type].test_and_set()) {
                schedule(CleanupTask(next_type));
                return;
            }

            switch (task.type) {

                $cases
                default: POMAGMA_ERROR("bad cleanup type" << task.type);
            }

            schedule(CleanupTask(next_type));
        }
        ''',
        bar = bar,
        type_count = type_count,
        cases = wrapindent(cases, '        '),
        ).newline()


def write_event_tasks(code, sequents):

    code('''
        $bar
        // event tasks
        ''',
        bar = bar,
        )

    event_tasks = {}
    for sequent in sequents:
        for event in compiler.get_events(sequent):
            tasks = event_tasks.setdefault(event.name, [])
            tasks += compiler.compile_given(sequent, event)

    event_tasks = event_tasks.items()
    event_tasks.sort(key=(lambda (name, tasks): (len(tasks), len(name), name)))
    for event, tasks in event_tasks:
        tasks.sort(key=(lambda (cost, _): cost))

        body = Code()
        for i, (cost, strategy) in enumerate(tasks):
            body('// cost = $cost', cost = cost)
            strategy.cpp(body)
            if i:
                body.newline()

        code('''
            void execute (const ${arity}Task & task)
            {
                $body
            }
            ''',
            arity = signature.get_arity(event),
            body = wrapindent(body),
            ).newline()


def get_functions_used_in(sequents):
    functions = {arity: [] for arity in signature.FUNCTION_ARITIES}
    symbols = set()
    for seq in sequents:
        assert isinstance(seq, Sequent)
        for expr in seq.antecedents | seq.succedents:
            symbols |= set(expr.polish.split())
    for c in symbols:
        if signature.is_fun(c):
            functions[signature.get_arity(c)].append(c)
    for val in functions.itervalues():
        val.sort()
    return functions


def write_theory(code, sequents):

    sequents = set(sequents)
    functions = get_functions_used_in(sequents)

    code('''
        #include "util.hpp"
        #include "carrier.hpp"
        #include "nullary_function.hpp"
        #include "injective_function.hpp"
        #include "binary_function.hpp"
        #include "symmetric_function.hpp"
        #include "binary_relation.hpp"
        #include "scheduler.hpp"
        #include <atomic>
        #include <vector>
        
        namespace pomagma {
        ''').newline()

    write_signature(code, functions)
    write_ensurers(code, functions)
    write_full_tasks(code, sequents)
    write_event_tasks(code, sequents)

    code('''
        } // namespace pomagma
        ''')

    return code
