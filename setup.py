import setuptools
from parsable import parsable

# Use parsable to find entry points dynamically
entry_points = parsable.find_entry_points("pomagma")

setuptools.setup(
    entry_points=entry_points,
)
