import json


def save(name, data):
    filename = f"{name}.json"
    print("saving"), filename
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def DEFINE(name, code):
    return {"name": name, "code": code}


def ASSERT(code):
    return {"name": None, "code": code}


TOP = {"is_top": True, "is_bot": False}
BOT = {"is_top": False, "is_bot": True}
OK = {"is_top": False, "is_bot": False}

save(
    "simplify_examples",
    [
        ("TOP", "TOP"),
        ("BOT", "BOT"),
        ("I", "I"),
        ("APP I I", "I"),
        ("COMP I I", "I"),
        ("JOIN BOT TOP", "TOP"),
    ],
)

save(
    "validate_examples",
    [
        (BOT, "BOT"),
        (TOP, "TOP"),
        (OK, "I"),
        (OK, "APP I I"),
        (OK, "COMP I I"),
    ],
)

save(
    "corpus",
    [
        (TOP, ASSERT("TOP")),
        (BOT, ASSERT("BOT")),
        (OK, ASSERT("I")),
        (OK, DEFINE("true", "K")),
        (OK, DEFINE("false", "APP K I")),
        # \x,f. f x
        # = \x. C I x
        # = C I
        (OK, DEFINE("box", "APP C I")),
        (OK, ASSERT("APP I APP VAR box I")),
        # \x,y,f. f x y
        # = \x,y. C (C I x) y
        # = \x. C (C I x)
        # = C * (C I)
        (OK, DEFINE("push", "COMP C VAR box")),
        # recursion
        (OK, DEFINE("push_unit", "APP C APP VAR box I")),
        (OK, ASSERT("APP VAR push_unit BOT")),
        (OK, ASSERT("APP VAR push_unit TOP")),
        (OK, DEFINE("uuu", "APP VAR push_unit VAR uuu")),
        # mutual recursion
        (OK, DEFINE("push_true", "APP C APP VAR box VAR true")),
        (OK, DEFINE("push_false", "APP C APP VAR box VAR false")),
        (OK, DEFINE("tftftf", "APP VAR push_true VAR ftftft")),
        (OK, DEFINE("ftftft", "APP VAR push_false VAR tftftf")),
        # join atoms
        (OK, DEFINE("join", "JOIN VAR true VAR false")),
        (OK, DEFINE("fix", "Y")),
        (OK, DEFINE("idem", "U")),
        (OK, DEFINE("close", "V")),
        (OK, DEFINE("close.sub", "P")),
        (OK, DEFINE("close.forall", "A")),
        # axioms
        (OK, ASSERT("EQUAL I APP APP S K K")),
        (OK, ASSERT("EQUAL B APP APP S APP K S K")),
        (OK, ASSERT("EQUAL CB APP C B")),
        (OK, ASSERT("EQUAL C APP APP S APP APP B B S APP K K")),
        (OK, ASSERT("EQUAL W APP APP C S I")),
        (OK, ASSERT("EQUAL Y APP APP APP S B CB APP W I")),
    ],
)
