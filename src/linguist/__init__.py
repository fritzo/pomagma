import os
import pomagma.util
import pomagma.analyst
import pomagma.language.util


JSON = os.path.join(pomagma.util.LANGUAGE, '{}.json')
PROTO = os.path.join(pomagma.util.LANGUAGE, '{}.language')


def fit_language(
        theory,
        address=pomagma.analyst.ADDRESS,
        log_file=None,
        log_level=0):

    language_json = JSON.format(theory)
    language_proto = PROTO.format(theory)

    def log_print(message, level):
        if level >= log_level:
            if log_file:
                pomagma.util.log_print(message, log_file)
            else:
                print message

    log_print('fitting language', pomagma.util.LOG_LEVEL_INFO)
    db = pomagma.analyst.connect(address)
    new_weights = db.fit_language()

    log_print('converting language', pomagma.util.LOG_LEVEL_DEBUG)
    language = pomagma.language.util.json_load(language_json)
    new_terms = sorted(new_weights.iterkeys())
    old_terms = sorted(key for group in language.itervalues() for key in group)
    assert new_terms == old_terms, '\n  '.join([
        'language mismatch,'
        'expected: {}'.format(old_terms),
        'actual: {}'.format(new_terms),
    ])
    for group in language:
        for key in group:
            group[key] = new_weights[key]

    log_print('writing {}'.format(language_json), pomagma.util.LOG_LEVEL_INFO)
    pomagma.language.util.json_dump(language, language_json)

    log_print('writing {}'.format(language_proto), pomagma.util.LOG_LEVEL_INFO)
    pomagma.language.util.compile(language_json, language_proto)
