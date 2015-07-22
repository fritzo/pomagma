import os
import re
import setuptools

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


def find_entry_points():
    points = []
    src = os.path.join(os.path.dirname(__file__), 'pomagma')
    for root, dirnames, filenames in os.walk(src, followlinks=True):
        for filename in filenames:
            if filename.endswith('.py'):
                path = os.path.join(root, filename)
                path = os.path.relpath(path, os.path.dirname(src))
                with open(path) as f:
                    for line in f:
                        if re.search('^import parsable', line):
                            module = path[:-3].replace('/', '.')
                            name = module.replace('.__main__', '')
                            points.append('{} = {}'.format(name, module))
                            break
    return map('{}:parsable.dispatch'.format, points)


version = None
with open(os.path.join('src', '__init__.py')) as f:
    for line in f:
        if re.match("__version__ = '\S+'$", line):
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
    'entry_points': {'console_scripts': find_entry_points()},
}

setuptools.setup(**config)
