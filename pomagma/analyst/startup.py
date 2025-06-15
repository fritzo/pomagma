# This file is intended to be used as a startup script with PYTHONSTARTUP.

from pomagma import __version__
from pomagma.analyst import connect as db

db = db()
print(f"Pomagma {__version__}. Type help(db) for more information on client.")

for name in dir(db):
    if not name.startswith("_"):
        locals()[name] = getattr(db, name)
del name
