## Using a Pomagma Client Library

Pomagma currently has a client library in [python](#python).
The python API includes internal database testing methods
that are not documented here.

See [analyst/test.py](/src/analyst/test.py) for example python usage.<br/>

### Python client <a name=python></a>

    $ python
    >>> from pomagma import analyst
    >>> db = analyst.connect('tcp://pomagma.org:34936')
    >>> db.ping()
    >>> db.simplify(["APP I I"])
    [I]
    >>> db.validate(["I"])
    [{"is_bot": False, "is_top": False}]
    >>> db.validate_corpus([
    ...     {"name": "zero", "code": "K"},
    ...     {"name": "succ", "code": "APP S B"},
    ...     {"name": None, "code": "APP succ APP succ zero"}])
    [{"is_bot": False, "is_top": False},
     {"is_bot": False, "is_top": False},
     {"is_bot": False, "is_top": False}]
