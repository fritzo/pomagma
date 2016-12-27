#!/usr/bin/env python

import csv
import glob
import hashlib
import os
import sys

from parsable import parsable

REPO = os.path.dirname(os.path.abspath(__file__))
VETTED = os.path.join(REPO, 'vetted_hashes.csv')
FILES_TO_VET = [
    'src/theory/*.facts',
    'src/theory/*.programs',
    'src/theory/*.symbols',
    'src/theory/*.tasks',
]


def hash_file(filename, blocksize=8192):
    hasher = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(blocksize)
            if data:
                hasher.update(data)
            else:
                break
    return hasher.hexdigest()


def hash_files(filenames):
    return {
        filename: hash_file(filename)
        for filename in filenames
        if os.path.exists(filename)
    }


def read_vetted_hashes():
    with open(VETTED) as f:
        reader = csv.reader(f)
        header = reader.next()
        assert header == ['filename', 'hexdigest'], header
        hashes = {filename: hexdigest for filename, hexdigest in reader}
    return hashes


def write_vetted_hashes(hashes):
    with open(VETTED, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'hexdigest'])
        for filename, hexdigest in sorted(hashes.iteritems()):
            writer.writerow([filename, hexdigest])


@parsable
def vet(*filenames):
    """Save hashes of current file versions for specified files.

    Use "vet all" to vet all files.

    """
    hashes = read_vetted_hashes()
    if list(filenames) == ['all']:
        filenames = hashes.keys()
    for filename in filenames:
        if filename in hashes:
            if os.path.exists(filename):
                print 'Updating', filename
                hashes[filename] = hash_file(filename)
            else:
                print 'Removing', filename
                del hashes[filename]
        else:
            print 'Adding', filename
            hashes[filename] = hash_file(filename)
    write_vetted_hashes(hashes)


def check_diffs(actual, expected):
    failures = sorted(
        filename
        for filename in expected
        if filename in actual
        if actual[filename] != expected[filename])
    if failures:
        print 'Files differ from vetted versions:'
        for filename in failures:
            print ' ', filename
        print 'Use "./diff.py codegen" to see differences.'
        print 'Use "./vet.py vet" to vet the changed files.'
    return failures


def check_missing(actual, expected):
    failures = sorted(
        filename
        for filename in expected
        if filename not in actual)
    if failures:
        print 'Files have not been generated:'
        for filename in failures:
            print ' ', filename
        print 'Use "make" to generate files if they should still exist.'
        print 'Use "./vet.py vet -filename" to remove files.'
    return failures


def check_unknown(actual, expected):
    failures = sorted(
        filename
        for pattern in FILES_TO_VET
        for filename in glob.glob(pattern)
        if filename not in expected)
    if failures:
        print 'Files have no vetted versions:'
        for filename in failures:
            print ' ', filename
        print 'Use "./vet.py vet filename" to add new files.'
    return failures


@parsable
def check():
    """Check files against vetted hashes."""
    expected = read_vetted_hashes()
    actual = hash_files(expected)
    if (check_diffs(actual, expected) or
            check_missing(actual, expected) or
            check_unknown(actual, expected)):
        sys.exit(1)


if __name__ == '__main__':
    parsable()
