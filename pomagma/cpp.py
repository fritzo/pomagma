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
        Ob $var = *iter;
        ''',
        var = self.var,
        )
    for var, expr in self.lets.iteritems():
        body('''
            Ob $var = $fun.find($args);
            ''',
            var = var,
            fun = expr.name,
            args = ', '.join(map(str, expr.args)))
    self.body.cpp(body)
    sets = []
    for test in self.tests:
        assert test.name in ['LESS', 'NLESS']
        lhs, rhs = test.args
        assert lhs != rhs
        if self.var == lhs:
            sets.append('%s.get_Rx_set(%s)' % (test.name, rhs))
        else:
            sets.append('%s.get_Lx_set(%s)' % (test.name, lhs))
    for expr in self.lets.itervalues():
        assert self.var in expr.args
        if len(expr.args) == 1:
            sets.append('%s.get_set()' % expr.name)
        else:
            lhs, rhs = expr.args
            assert lhs != rhs
            if self.var == lhs:
                sets.append('%s.get_Rx_set(%s)' % (expr.name, rhs))
            else:
                sets.append('%s.get_Lx_set(%s)' % (expr.name, lhs))
    if len(sets) == 0:
        code('''
            const DenseSet & set = carrier.support();
            ''')
    elif len(sets) == 1:
        code('''
            DenseSet set($one_set, yes_copy_construct);
            ''',
            one_set = iter(sets).next())
    else:
        code('''
            DenseSet set(carrier.item_dim());
            set.set_union($sets);
            ''',
            sets = ', '.join(sets),
            )
    code('''
        for (DenseSet::Iter iter(set); iter.ok(); iter.next()) {
            $body
        }
        ''',
        body=wrapindent(body),
        )


@methodof(compiler.IterInvInjective)
def cpp(self, code):
    body = Code('''
        Ob $var = iter.arg();
        ''', var=self.var)
    self.body.cpp(body)
    code('''
        for ($Iter iter($value); iter.ok(); iter.next()) {
            $body
        }
        ''',
        Iter = 'InjectiveFunction::inverse_iterator',
        value = self.value,
        body = wrapindent(body),
        )


@methodof(compiler.IterInvBinary)
def cpp(self, code):
    body = Code('''
        Ob $var1 = iter.lhs();
        Ob $var2 = iter.rhs();
        ''',
        var1 = self.var1,
        var2 = self.var2,
        )
    self.body.cpp(body)
    code('''
        for ($Iter iter($value); iter.ok(); iter.next()) {
            $body
        }
        ''',
        Iter = 'BinaryFunction::inverse_iterator',
        value = self.value,
        body = wrapindent(body),
        )


@methodof(compiler.IterInvBinaryRange)
def cpp(self, code):
    body = Code('''
        Ob $var = iter.$moving();
        ''',
        var = self.var2 if self.lhs_fixed else self.var1,
        moving = 'rhs' if self.lhs_fixed else 'lhs',
        )
    self.body.cpp(body)
    code('''
        for ($Iter iter($var1, $var2); iter.ok(); iter.next()) {
            $body
        }
        ''',
        Iter = 'BinaryFunction::inv_range_iterator',
        var1 = self.value,
        var2 = self.var2 if self.lhs_fixed else self.var1,
        body = wrapindent(body),
        )


@methodof(compiler.Let)
def cpp(self, code):
    body = Code()
    self.body.cpp(body)
    code('''
        if (Ob $var = $fun.find($args)) {
            $body
        }
        ''',
        var = self.var,
        fun = self.expr.name,
        args = ', '.join(map(str, self.expr.args)),
        body = wrapindent(body),
        )


@methodof(compiler.Test)
def cpp(self, code):
    body = Code()
    self.body.cpp(body)
    # TODO FIXME this fails with self.expr = I, Y
    #assert self.expr.name in ['EQUAL', 'LESS', 'NLESS'], self.expr
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
        
        $funs
        ''',
        bar = bar,
        funs = funs,
        ).newline()

def write_ensurers(code, functions):

    code('''
        $bar
        // ensurers
        ''',
        bar = bar,
        ).newline()

    functions = [(name, arity, signature.get_nargs(arity))
                 for arity, funs in functions.iteritems()
                 if signature.get_nargs(arity) > 0
                 for name in funs]

    def Ob(x):
        return 'Ob %s' % x

    for name, arity, argc in functions:
        vars_ = ['key'] if argc == 1 else ['lhs', 'rhs']
        code('''
            inline void ensure_${name} ($typed_args, Ob val)
            {
                if (Ob old_val = $NAME($args)) {
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
            typed_args=', '.join(map(Ob, vars_)),
            arity=arity,
            ).newline()

    for name1, arity1, argc1 in functions:
        for name2, arity2, argc2 in functions:
            if name1 > name2:
                continue

            vars1 = ['key1'] if argc1 == 1 else ['lhs1', 'rhs1']
            vars2 = ['key2'] if argc2 == 1 else ['lhs2', 'rhs2']
            code('''
                inline void ensure_${name1}_${name2} (
                    $typed_args1,
                    $typed_args2)
                {
                    if (Ob val1 = $NAME1.find($args1)) {
                        ensure_${name2}($args2, val1);
                    } else {
                        if (Ob val2 = $NAME2.find($args2)) {
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
                typed_args1 = ', '.join(map(Ob, vars1)),
                typed_args2 = ', '.join(map(Ob, vars2)),
                arity1 = arity,
                arity2 = arity2,
                ).newline()


def write_merge_task(code, functions):
    TODO()
    body = Code()
    body('''
        const Ob dep = task.dep;
        const Ob rep = carrier.find(dep);
        POMAGMA_ASSERT(dep < rep, "bad merge: " << dep << ", " << rep);
        ''')

    for name, arity, argc in functions:
        # TODO provide merge(-,-) for injective_fun
        body('''
            $name.merge(dep, rep);
            ''',
            name = name,
            )

    body('''
        carrier.remove(dep);
        '''
        )

    code('''
        void execute (const ${groupname}Task & task)
        {
            $body
        }
        ''',
        body = wrapindent(body),
        )


def write_full_tasks(code, sequents):

    full_tasks = []
    for sequent in sequents:
        full_tasks += compiler.compile_full(sequent)
    full_tasks.sort(key=(lambda (cost, _): cost))
    type_count = len(full_tasks)

    cases = Code()
    for i, (cost, strategy) in enumerate(full_tasks):
        if i:
            cases.newline()
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
            )

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
        ).newline()

    event_tasks = {}
    for sequent in sequents:
        for event in compiler.get_events(sequent):
            tasks = event_tasks.setdefault(event.name, [])
            tasks += compiler.compile_given(sequent, event)

    def get_group(name):
        relations = {
            'LESS': 'PositiveOrder',
            'NLESS': 'NegativeOrder',
            }
        return relations.get(name, signature.get_arity(name))

    group_tasks = {}
    for name, tasks in event_tasks.iteritems():
        groupname = get_group(name)
        group_tasks.setdefault(groupname, {})[name] = tasks

    # TODO sort groups
    #event_tasks = event_tasks.items()
    #event_tasks.sort(key=(lambda (name, tasks): (len(tasks), len(name), name)))
    for tasks in event_tasks.itervalues():
        tasks.sort(key=(lambda (cost, _): cost))

    group_tasks = list(group_tasks.iteritems())
    group_tasks.sort()

    for groupname, group in group_tasks:
        group = list(group.iteritems())
        group.sort()

        body = Code()

        for g, (event, tasks) in enumerate(group):
            if g:
                body.newline()

            subbody = Code()
            for i, (cost, strategy) in enumerate(tasks):
                if i:
                    subbody.newline()
                subbody('// cost = $cost', cost = cost)
                strategy.cpp(subbody)

            if event in ['LESS', 'NLESS']:
                body(str(subbody))
            else:
                body('''
                if (task.fun == & $event) {

                    $subbody
                }
                ''',
                event = event,
                subbody = wrapindent(subbody),
                )

        code('''
            void execute (const ${groupname}Task & task)
            {
                $body
            }
            ''',
            groupname = groupname,
            body = wrapindent(body),
            ).newline()


def get_functions_used_in(sequents):
    functions = dict((arity, []) for arity in signature.FUNCTION_ARITIES)
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
        #include "theory.hpp"
        
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
