import os

import pomagma.analyst
import pomagma.language.util
import pomagma.util

JSON = os.path.join(pomagma.util.LANGUAGE, "{}.json")
PROTO = os.path.join(pomagma.util.LANGUAGE, "{}.language")


def fit_language(theory, address=pomagma.analyst.ADDRESS, log_file=None, log_level=0):
    language_json = JSON.format(theory)
    language_proto = PROTO.format(theory)

    def log_print(message, level):
        if level >= log_level:
            if log_file:
                pomagma.util.log_print(message, log_file)
            else:
                print(message)

    log_print("fitting language", pomagma.util.LOG_LEVEL_INFO)
    with pomagma.analyst.connect(address) as db:
        new_weights = db.fit_language()

    log_print("converting language", pomagma.util.LOG_LEVEL_DEBUG)
    language = pomagma.language.util.json_load(language_json)
    new_terms = sorted(new_weights.keys())
    old_terms = sorted(key for group in list(language.values()) for key in group)
    assert new_terms == old_terms, "\n  ".join(
        [
            f"language mismatch,expected: {old_terms}",
            f"actual: {new_terms}",
        ]
    )
    for group in language:
        for key in group:
            group[key] = new_weights[key]

    log_print(f"writing {language_json}", pomagma.util.LOG_LEVEL_INFO)
    pomagma.language.util.json_dump(language, language_json)

    log_print(f"writing {language_proto}", pomagma.util.LOG_LEVEL_INFO)
    pomagma.language.util.compile(language_json, language_proto)
