import os
import re

import setuptools
from parsable import parsable

# TODO add MANIFEST.in as described in
# http://docs.python.org/2/distutils/sourcedist.html#the-manifest-in-template

# package_dir is not compatible with 'pip install -e'
# packages = [
#     re.sub('^src','pomagma', name)
#     for name in setuptools.find_packages()
# ]
# for name in packages:
#     print name
#
# setuptools.setup(
#     name='pomagma',
#     packages=packages,
#     package_dir={'pomagma': 'src'},
# )


version = None
with open(os.path.join('src', '__init__.py')) as f:
    for line in f:
        if re.match(r"__version__ = '\S+'$", line):
            version = line.split()[-1].strip("'")
assert version, 'could not determine version'

with open('README.md') as f:
    long_description = f.read()

config = {
    'name': 'pomagma',
    'version': version,
    'description': 'An inference engine for extensional lambda-calculus',
    'long_description': long_description,
    'url': 'https://github.com/fritzo/pomagma',
    'author': 'Fritz Obermeyer',
    'maintainer': 'Fritz Obermeyer',
    'maintainer_email': 'fritz.obermeyer@gmail.com',
    'license': 'Apache 2.0',
    'packages': setuptools.find_packages(exclude='src'),
    'entry_points': parsable.find_entry_points('pomagma'),
    'install_requires': [
        'black>=21.4b0',
        'boto',
        'contextlib2',
        'flake8',
        'hypothesis',
        'ipython==7.16.3',
        'isort>=5.0',
        'mock',
        'mypy>=0.8.12',
        'nbval',
        'parsable>=0.2.0',
        'protobuf<3.0',
        'psutil',
        'pytest-timeout',
        'pytest-xdist',
        'pytest>=5',
        'pyzmq',
    ],
}

setuptools.setup(**config)
