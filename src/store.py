import os
import shutil
import functools
import subprocess
import urllib
import contextlib
import tempfile
import boto


BUCKET = boto.connect_s3().get_bucket('pomagma')


def s3_put(filename):
    key = BUCKET.new_key(filename)
    key.set_contents_from_filename(filename)


def s3_get(filename):
    key = BUCKET.get_key(filename)
    key.get_contents_to_filename(filename)


def bzip2(filename):
    subprocess.check_call(['bzip2', filename])


def bunzip2(filename):
    subprocess.check_call(['bunzip2', filename])
