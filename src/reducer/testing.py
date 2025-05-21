"""Tools for testing implementations of reduce() and simplify()."""

import os
from importlib import import_module

import hypothesis.strategies as s
import pytest
from parsable import parsable

from pomagma.reducer import bohm
from pomagma.reducer.linker import link
from pomagma.reducer.syntax import (
    APP,
    BOOL,
    BOT,
    CODE,
    EQUAL,
    EVAL,
    JOIN,
    MAYBE,
    NVAR,
    QAPP,
    QEQUAL,
    QLESS,
    QQUOTE,
    QUOTE,
    TOP,
    UNIT,
    B,
    C,
    I,
    K,
    S,
    Y,
    is_app,
    is_equal,
    is_quote,
    sexpr_parse,
    sexpr_print,
)

DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(DIR, "testdata")


# ----------------------------------------------------------------------------
# parameterized testing


def iter_test_cases(test_id, suites=None):
    assert isinstance(test_id, str), test_id
    print(("test_id = {}".format(test_id)))
    if suites is None:
        module = import_module("pomagma.reducer.{}".format(test_id))
        suites = module.SUPPORTED_TESTDATA
    for suite in suites:
        basename = "{}.sexpr".format(suite)
        filename = os.path.join(TESTDATA, basename)
        print(("reading {}".format(filename)))
        with open(filename) as f:
            for i, line in enumerate(f):
                parts = line.split(";", 1)
                sexpr = parts[0].strip()
                if sexpr:
                    message = "In {}:{}\n{}".format(basename, 1 + i, line)
                    try:
                        term = sexpr_parse(sexpr)
                    except ValueError as e:
                        raise ValueError("{} {}".format(message, e))
                    comment = None if len(parts) < 2 else parts[1].strip()
                    yield term, comment, message


def parse_xfail(comment, test_id):
    if comment.startswith("xfail"):
        if test_id is None:
            return True
        if test_id in comment[len("xfail") :].strip().split(" "):
            return True
    return False


def iter_equations(test_id, suites=None):
    assert isinstance(test_id, str), test_id
    for term, comment, message in iter_test_cases(test_id, suites):
        if is_equal(term):
            lhs = link(bohm.convert(term[1]))
            rhs = link(bohm.convert(term[2]))
            example = lhs, rhs, message
            if comment and parse_xfail(comment, test_id):
                example = pytest.mark.xfail(example)
            yield example
        else:
            raise NotImplementedError(message)


def migrate(fun):
    """Applies a term->term transform on all files in testdata/."""
    for basename in os.listdir(TESTDATA):
        assert basename.endswith(".sexpr"), basename
        print(("processing {}".format(basename)))
        filename = os.path.join(TESTDATA, basename)
        lines = []
        with open(filename) as f:
            for lineno, line in enumerate(f):
                line = line.strip()
                parts = line.split(";", 1)
                sexpr = parts[0].strip()
                comment = "" if len(parts) == 1 else parts[1]
                if sexpr:
                    term = sexpr_parse(sexpr)
                    try:
                        term = fun(term)
                    except Exception:
                        print(("Error at {}:{}".format(basename, lineno + 1)))
                        print(line)
                        raise
                    sexpr = sexpr_print(term)
                if not comment:
                    line = sexpr
                elif not sexpr:
                    line = ";{}".format(comment)
                else:
                    line = "{}  ;{}".format(sexpr, comment)
                lines.append(line)
        with open(filename, "w") as f:
            for line in lines:
                f.write(line)
                f.write("\n")
    print("done")


@parsable
def reformat():
    """Reformat all files in testdata/."""
    migrate(lambda x: x)


def _unquote_equal(term):
    if not is_app(term) or not is_app(term[1]) or term[1][1] is not EQUAL:
        return term
    lhs = term[1][2]
    rhs = term[2]
    assert is_quote(lhs), lhs
    assert is_quote(rhs), rhs
    lhs = lhs[1]
    rhs = rhs[1]
    return APP(APP(EQUAL, lhs), rhs)


@parsable
def unquote_equal():
    """Convert (EQUAL (QUOTE x) (QUOTE y)) to (EQUAL x y)."""
    migrate(_unquote_equal)


# ----------------------------------------------------------------------------
# property-based testing

alphabet = "_abcdefghijklmnopqrstuvwxyz"
s_vars = s.builds(
    NVAR,
    s.builds(str, s.text(alphabet=alphabet, min_size=1, average_size=5)),
)

s_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(Y),
    s.one_of(
        s.just(CODE),
        s.just(EVAL),
        s.just(QAPP),
        s.just(QQUOTE),
        s.just(QEQUAL),
        s.just(QLESS),
    ),
    s.one_of(
        s.just(UNIT),
        s.just(BOOL),
        s.just(MAYBE),
    ),
)
s_sk_atoms = s.one_of(
    s.one_of(s_vars),
    s.just(TOP),
    s.just(BOT),
    s.just(I),
    s.just(K),
    s.just(B),
    s.just(C),
    s.just(S),
    s.just(Y),
)


def s_sk_extend(terms):
    return s.builds(APP, terms, terms)


def s_skj_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
    )


def s_terms_extend(terms):
    return s.one_of(
        s.builds(APP, terms, terms),
        s.builds(JOIN, terms, terms),
        s.builds(QUOTE, terms),
    )


s_sk_terms = s.recursive(s_sk_atoms, s_sk_extend, max_leaves=100)
s_skj_terms = s.recursive(s_sk_atoms, s_skj_extend, max_leaves=100)
s_terms = s.recursive(s_atoms, s_terms_extend, max_leaves=100)
s_quoted = s.builds(QUOTE, s_terms)


if __name__ == "__main__":
    parsable()
