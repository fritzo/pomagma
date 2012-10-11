from setuptools import setup, find_packages

# HACK ./pomagma symlinks to ./src/ because I cannot find a
# setuptools.setup option to specify source location
setup(
    name='pomagma',
    packages=find_packages(exclude='src'),
)
