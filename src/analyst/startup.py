# This file is intended to be used as a startup script with PYTHONSTARTUP.

from pomagma.analyst import connect as db
from pomagma import __version__

db = db()
print 'Pomagma {}. Type help(db) for more information on client.'.format(
    __version__)

for name in dir(db):
    if not name.startswith('_'):
        locals()[name] = getattr(db, name)
del name
