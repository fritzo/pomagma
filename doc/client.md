## Using a Pomagma Client Library

Pomagma currently has client libraries in
[python](#python) and
[javascript](#js),
and it is easy to write a new client library
in any language that supports
[zeromq](http://zeromq.org/bindings:_start) and
[protocol buffers](https://developers.google.com/protocol-buffers/docs/reference/other).
The python API includes internal database testing methods
that are not documented here.

See [analyst/test.py](/src/analyst/test.py) for example python usage.<br/>
See [analyst/test.js](/src/analyst/test.js) for example node.js usage.<br/>
See the [Puddle](https://github.com/fritzo/puddle) project for more complete
usage, e.g. [main.js](https://github.com/fritzo/puddle/blob/master/main.js).

### Python client <a name=python></a>

    python
    from pomagma import analyst
    ADDRESS = "tcp://pomagma.org:34936"
    with analyst.connect(ADDRESS) as db:

        db.ping()

        print db.simplify(["APP I I"])
        # [I]

        print db.validate(["I"])
        # [{"is_bot": False, "is_top": False}]

        print db.validate_corpus([
            {"name": "zero", "code": "K"},
            {"name": "succ", "code": "APP S B"},
            {"name": None, "code": "APP succ APP succ zero"}])
        # [{"is_bot": False, "is_top": False},
        #  {"is_bot": False, "is_top": False},
        #  {"is_bot": False, "is_top": False}]
            

### Node.js client <a name=js></a>

    node
    var ADDRESS = "tcp://pomagma.org:34936";
    db = require("pomagma").connect(ADDRESS);

    db.ping()

    db.simplify(["APP I I"])
    // [I]

    print db.validate(["I"])
    // [{"is_bot": False, "is_top": False}]

    print db.validateCorpus([
        {"name": "zero", "code": "K"},
        {"name": "succ", "code": "APP S B"},
        {"name": null, "code": "APP succ APP succ zero"}
    ])
    // [
    //    {"is_bot": False, "is_top": False},
    //    {"is_bot": False, "is_top": False},
    //    {"is_bot": False, "is_top": False}
    // ]

    db.close()
