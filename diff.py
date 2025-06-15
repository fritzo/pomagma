#!/usr/bin/env python

import contextlib
import os
import subprocess

from parsable import parsable

REPO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(REPO)
TEMP = os.path.join(ROOT, f"{os.path.basename(REPO)}-temp")
DIFFTOOL = os.environ.get("POMAGMA_DIFFTOOL", os.environ.get("EDITOR", "meld"))


def get_difftool(tool, left, right, diffignore):
    if tool == "diff":
        return [
            "diff",
            "-r",
            *list(map("--exclude={}".format, diffignore)),
            left,
            right,
        ]
    if tool == "cdiff":
        return ["cdiff", "-s", "-w", "0", left, right]
    if tool == "vim":
        return [
            "vim",
            "-c",
            'let g:DirDiffExcludes = "{}"'.format(",".join(diffignore)),
            "-c",
            f"DirDiff {left} {right}",
        ]
    if tool == "gvim":
        return [
            "gvim",
            "-geom",
            "165x80",
            "-c",
            'let g:DirDiffExcludes = "{}"'.format(",".join(diffignore)),
            "-c",
            f"DirDiff {left} {right}",
        ]
    if tool == "mvim":
        return [
            "mvim",
            "-c",
            "set columns=165",
            "-c",
            'let g:DirDiffExcludes = "{}"'.format(",".join(diffignore)),
            "-c",
            f"DirDiff {left} {right}",
        ]
    return [tool, left, right]


def parallel_check_call(*args):
    processes = [subprocess.Popen(args) for args in args]
    for process in processes:
        process.wait()


@contextlib.contextmanager
def chdir(destin):
    source = os.path.abspath(os.curdir)
    try:
        print(f"# cd {destin}")
        os.chdir(destin)
        yield
    finally:
        print(f"# cd {source}")
        os.chdir(source)


@parsable
def clone(commit="HEAD"):
    """Create temporary clone repo in ../ positioned at the given commit."""
    with chdir(REPO):
        commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", commit]
        ).strip()

    if os.path.exists(TEMP):
        print(f"using clone {TEMP}")
        with chdir(TEMP):
            subprocess.check_call(["git", "fetch", "--all"])
    else:
        print(f"cloning to {TEMP}")
        with chdir(ROOT):
            subprocess.check_call(["git", "clone", REPO, TEMP])

    with chdir(TEMP):
        subprocess.check_call(["git", "checkout", commit])


@parsable
def codegen(commit="HEAD", difftool=DIFFTOOL):
    """
    Diff generated code pomagma/theory/*.symbols, *.programs, *.facts, *.tasks
    Supported difftools: diff, meld, cdiff, vim, gvim, mvim
    """
    clone(commit=commit)
    parallel_check_call(
        ["make", "-C", REPO, "codegen", "codegen-summary"],
        ["make", "-C", TEMP, "codegen", "codegen-summary"],
    )
    subprocess.check_call(
        get_difftool(
            difftool,
            os.path.join(REPO, "pomagma", "theory"),
            os.path.join(TEMP, "pomagma", "theory"),
            diffignore=[
                # '*.tasks',
                "*.rules",
                "*.theory",
                "*.pyc",
            ],
        )
    )


@parsable
def codegen_summary(commit="HEAD", difftool=DIFFTOOL):
    """
    Diff generated code sommary in pomagma/theory/*.tasks.
    Supported difftools: diff, meld, cdiff, vim, gvim, mvim
    """
    clone(commit=commit)
    parallel_check_call(
        ["make", "-C", REPO, "codegen-summary"], ["make", "-C", TEMP, "codegen-summary"]
    )
    subprocess.check_call(
        get_difftool(
            difftool,
            os.path.join(REPO, "pomagma", "theory"),
            os.path.join(TEMP, "pomagma", "theory"),
            diffignore=[
                "*.symbols",
                "*.programs",
                "*.facts",
                "*.rules",
                "*.theory",
                "*.pyc",
            ],
        )
    )


if __name__ == "__main__":
    parsable()
