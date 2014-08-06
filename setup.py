#import re
from setuptools import setup, find_packages

# TODO add MANIFEST.in as described in
# http://docs.python.org/2/distutils/sourcedist.html#the-manifest-in-template

# package_dir is not compatible with 'pip install -e'
# packages = [
#    re.sub('^src','pomagma', name)
#    for name in find_packages()
#    ]
# for name in packages:
#    print name
#
# setup(
#    name='pomagma',
#    packages=packages,
#    package_dir={'pomagma': 'src'},
#    )

setup(
    name='pomagma',
    packages=find_packages(exclude='src'),
)
