# This file is intended to be used as a startup script with PYTHONSTARTUP.

from pomagma import __version__
from pomagma.analyst import connect as db

db = db()
print("Pomagma {}. Type help(db) for more information on client.".format(__version__))

for name in dir(db):
    if not name.startswith("_"):
        locals()[name] = getattr(db, name)
del name
