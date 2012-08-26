from textwrap import dedent
from pomagma.util import TODO, inputs, union, methodof
from pomagma import signature
from pomagma import compiler


def indent(text):
    return '    ' + text.replace('\n', '\n    ')


@methodof(compiler.Iter)
def cpp_lines(self):
    body = ['oid_t {0} = *iter;'.format(self.var)]
    for var, expr in self.lets.iteritems():
        body.append('oid_t {0} = {1}({2});'.format(
            var, expr.name, ', '.join(map(str, expr.args))))
    body += self.body.cpp_lines()
    body = map(indent, body)
    sets = []
    for test in self.tests:
        sets.append('TODO {0}'.format(str(test)))
    for var, expr in self.lets.iteritems():
        sets.append('TODO {0}'.format(str(var)))
    lines = []
    if len(sets) == 0:
        lines += [
            'const dense_set & set = carrier.support();',
            ]
    elif len(sets) == 1:
        one_set = iter(sets).next()
        lines += [
            'dense_set set(carrier.item_dim(), {0});'.format(one_set),
            ]
    else:
        lines += [
            'dense_set set(carrier.item_dim());',
            'set.set_union({0})'.format(', '.join(sets)),
            ]
    lines += [
        'for (dense_set::iterator iter(set); iter.ok(); iter.next()) {',
        ] + body + [
        '}',
        ]
    return lines


@methodof(compiler.IterInvInjective)
def cpp_lines(self):
    body = []
    body.append('oid_t {0} = iter.arg();'.format(self.var))
    body += self.body.cpp_lines()
    body = ['    ' + line for line in body]
    iter = 'InjectiveFunction::inverse_iterator iter({0})'.format(self.value)
    return [
        'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
        ] + body + [
        '}',
        ]


@methodof(compiler.IterInvBinary)
def cpp_lines(self):
    body = []
    body.append('oid_t {0} = iter.lhs();'.format(self.var1))
    body.append('oid_t {0} = iter.rhs();'.format(self.var2))
    body += self.body.cpp_lines()
    body = ['    ' + line for line in body]
    iter = 'BinaryFunction::inverse_iterator iter({0})'.format(self.value)
    return [
        'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
        ] + body + [
        '}',
        ]


@methodof(compiler.IterInvBinaryRange)
def cpp_lines(self):
    body = []
    if self.lhs_fixed:
        body.append('oid_t {0} = iter.rhs();'.format(self.var2))
    else:
        body.append('oid_t {0} = iter.lhs();'.format(self.var1))
    body += self.body.cpp_lines()
    body = ['    ' + line for line in body]
    if self.lhs_fixed:
        iter = 'BinaryFunction::inv_range_iterator iter({0}, {1})'.format(
                self.value, self.var2)
    else:
        iter = 'BinaryFunction::inv_range_iterator iter({0}, {1})'.format(
                self.value, self.var1)
    return [
        'for ({0}; iter.ok(); iter.next()) {{'.format(iter),
        ] + body + [
        '}',
        ]


@methodof(compiler.Let)
def cpp_lines(self):
    if self.expr.args:
        expr = str(self.expr)
    else:
        expr = 'signature::{0}()'.format(self.expr)
    return [
        'if (oid_t {0} = {1}) {{'.format(self.var, expr)
        ] + map(indent, self.body.cpp_lines()) + [
        '}'
        ]


@methodof(compiler.Test)
def cpp_lines(self):
    body = map(indent, self.body.cpp_lines())
    return [
        'if ({0}) {{'.format(self.expr)
        ] + body + [
        '}',
        ]


@methodof(compiler.Ensure)
def cpp_lines(self):
    expr = self.expr
    assert len(expr.args) == 2
    lhs, rhs = expr.args
    if lhs.is_var() and rhs.is_var():
        args = ', '.join(map(str, expr.args))
        return ['ensure_{0}({1});'.format(expr.name.lower(), args)]
    else:
        assert self.expr.name == 'EQUAL'
        if lhs.is_var():
            name = rhs.name.lower()
            args = ', '.join(map(str, rhs.args))
            return ['ensure_{0}({1}, {2});'.format(name, args, lhs)]
        elif rhs.is_var():
            name = lhs.name.lower()
            args = ', '.join(map(str, lhs.args))
            return ['ensure_{0}({1}, {2});'.format(name, args, rhs)]
        else:
            if rhs.name < lhs.name:
                lhs, rhs = rhs, lhs
            name = '{0}_{1}'.format(lhs.name.lower(), rhs.name.lower())
            args = ', '.join(map(str, lhs.args + rhs.args))
            return ['ensure_{0}({1});'.format(name, args)]


class Theory:
    def __init__(self, sequents):
        self.sequents = set(sequents)
        self.signature = {
            'NullaryFunction': [],
            'InjectiveFunction': [],
            'BinaryFunction': [],
            'SymmetricFunction': [],
            }
        symbols = set()
        for seq in sequents:
            for expr in seq.antecedents | seq.succedents:
                symbols |= set(expr.polish.split())
        for c in symbols:
            if signature.is_fun(c):
                self.signature[signature.get_arity(c)].append(c)
        for val in self.signature.itervalues():
            val.sort()

    def _write_signature(self, write, section):

        section('signature')
        write()

        write('namespace signature {')
        write()

        write('Carrier carrier;')
        write()

        write('BinaryRelation LESS(carrier);')
        write('BinaryRelation NLESS(carrier);')
        write()

        for arity, funs in self.signature.iteritems():
            for name in funs:
                write('{0} {1}(carrier);'.format(arity, name))
            if funs:
                write()

        write('} // namespace signature')
        write('using namespace signature;')
        write()

    def _write_ensurers(self, write, section):

        section('ensurers')
        write()

        write(dedent('''
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
        ''').strip())
        write()

        functions = [(name, arity, signature.get_nargs(arity))
                     for arity, funs in self.signature.iteritems()
                     for name in funs]

        def oid_t(x):
            return 'oid_t {0}'.format(x)

        for name, arity, argc in functions:
            vars_ = ['key'] if argc == 1 else ['lhs', 'rhs']
            write(dedent('''
            inline void ensure_{name} ({typed_args}, oid_t val)
            {{
                if (oid_t old_val = {NAME}({args})) {{
                    ensure_equal(old_val, val);
                }} else {{
                    {NAME}.insert({args}, val);
                    schedule({Arity}FunctionTask({NAME}, {args}));
                }}
            }}
            ''')
            .format(
                name=name.lower(),
                NAME=name,
                args=', '.join(vars_),
                typed_args=', '.join(map(oid_t, vars_)),
                Arity=arity.capitalize(),
                )
            .strip())
            write()

        for name1, arity1, argc1 in functions:
            for name2, arity2, argc2 in functions:
                if name2 > name1:
                    continue

                vars1 = ['key1'] if argc1 == 1 else ['lhs1', 'rhs1']
                vars2 = ['key2'] if argc2 == 1 else ['lhs2', 'rhs2']
                write(dedent('''
                inline void ensure_{name1}_{name2} (
                    {typed_args1},
                    {typed_args2})
                {{
                    if (oid_t val1 = {NAME1}({args1})) {{
                        ensure_{name2}({args2}, val1);
                    }} else {{
                        if (oid_t val2 = {NAME2}({args2})) {{
                            {NAME1}.insert({args1}, val2);
                            schedule({Arity1}FunctionTask({NAME1}, {args1}));
                        }}
                    }}
                }}
                ''')
                .format(
                    name1=name1.lower(),
                    name2=name2.lower(),
                    NAME1=name1,
                    NAME2=name2,
                    args1=', '.join(vars1),
                    args2=', '.join(vars2),
                    typed_args1=', '.join(map(oid_t, vars1)),
                    typed_args2=', '.join(map(oid_t, vars2)),
                    Arity1=arity.capitalize(),
                    Arity2=arity2.capitalize(),
                    )
                .strip())
                write()

    def _write_full_tasks(self, write, section):

        full_tasks = []
        for sequent in self.sequents:
            full_tasks += compiler.compile_full(sequent)
        full_tasks.sort(key=(lambda (cost, _): cost))
        type_count = len(full_tasks)

        section('full tasks')
        write(dedent('''

        const size_t g_type_count = {type_count};
        std::vector<std::atomic_flag> g_clean_state(g_type_count, true);

        void set_state_dirty ()
        {{
            for (auto & state : g_clean_state) {{
                state.clear();
            }}
        }}

        void execute (const CleanupTask & task)
        {{
            // HACK
            // TODO find a better cleanup scheduling policy
            size_t next_type = (task.type + 1) % g_type_count;
            if (task.type >= g_type_count) {{
                schedule(CleanupTask(0));
            }}
            if (not g_clean_state[task.type].test_and_set()) {{
                schedule(CleanupTask(next_type));
                return;
            }}

            switch (task.type)
            {{
        ''').rstrip().format(
            type_count=type_count
            ))

        for i, (cost, strategy) in enumerate(full_tasks):
            write()
            write('    case {0}: {{ // cost = {1}'.format(i, cost))
            for line in strategy.cpp_lines():
                write('        ' + line)
            write('    } break;')

        write(dedent('''
            default: POMAGMA_ERROR("bad cleanup type" << task.type);
            }

            schedule(CleanupTask(next_type));
        }
        '''))

    def _write_event_tasks(self, write, section):

        section('event tasks')
        write()

        event_tasks = {}
        for sequent in self.sequents:
            for event in compiler.get_events(sequent):
                tasks = event_tasks.setdefault(event.name, [])
                tasks += compiler.compile_given(sequent, event)

        event_tasks = sorted(
                event_tasks.items(),
                key=(lambda (name, tasks): (len(tasks), len(name), name)))
        for event, tasks in event_tasks:
            tasks.sort(key=(lambda (cost, _): cost))
            arity = signature.get_arity(event)
            write(dedent('''
            void execute (const {arity}Task & task)
            {{
            ''').rstrip().format(
                arity=arity
                ))

            for cost, strategy in tasks:
                write()
                write('    // cost = {0}'.format(cost))
                for line in strategy.cpp_lines():
                    write('    ' + line)

            write('}')

    def cpp_lines(self):
        lines = []

        def write(line_with_newlines=''):
            for line in line_with_newlines.split('\n'):
                lines.append(line)

        def section(name):
            write()
            write('//' + '-' * 76)
            write('// {0}'.format(name))

        self._write_signature(write, section)
        self._write_ensurers(write, section)
        self._write_full_tasks(write, section)
        self._write_event_tasks(write, section)

        return lines
