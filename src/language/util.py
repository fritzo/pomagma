import simplejson as json
import parsable
parsable = parsable.Parsable()
from pomagma.language.language_pb2 import Language, WeightedTerm


def json_load(filename):
    with open(filename) as f:
        return json.load(f)


def json_dump(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)


ARITY_TO_PB2 = {
    'NULLARY': WeightedTerm.NULLARY,
    'INJECTIVE': WeightedTerm.INJECTIVE,
    'BINARY': WeightedTerm.BINARY,
    'SYMMETRIC': WeightedTerm.SYMMETRIC,
}

ARITY_FROM_PB2 = {val: key for key, val in ARITY_TO_PB2.iteritems()}


def normalize_dict(grouped):
    '''
    L1-normalize the weights in a groupd dict in-place.
    '''
    total = sum(
        weight
        for group in grouped.itervalues()
        for weight in group.itervalues()
    )
    assert total > 0, "total weight is zero"
    scale = 1.0 / total

    for group in grouped.itervalues():
        for key in group:
            group[key] *= scale


def dict_to_language(grouped):
    '''
    Convert from grouped dict to protobuf format.

    Example Input:

        grouped = {
            'NULLARY': {
                'B': 1.0,
                'C': 1.30428,
                'I': 2.21841,
                'K': 2.6654,
                'S': 2.69459,
                },
            'BINARY': {
                'APP': 0.4,
                'COMP': 0.2,
                },
            #'INJECTIVE': {},  # empty, may be omitted
            #'SYMMETRIC': {},  # empty, may be omitted
            }
    '''
    grouped = grouped.copy()
    normalize_dict(grouped)
    language = Language()
    for arity, group in grouped.iteritems():
        for name, weight in group.iteritems():
            term = language.terms.add()
            term.name = name
            term.arity = ARITY_TO_PB2[arity.upper()]
            term.weight = weight

    return language


def language_to_dict(language):
    '''
    Convert from protobuf format to grouped dict.
    '''
    grouped = {}
    for term in language.terms:
        arity = ARITY_FROM_PB2[term.arity]
        grouped.setdefault(arity, {})[term.name] = term.weight
    return grouped


@parsable.command
def compile(json_in, language_out):
    '''
    Convert language from json to protobuf format.
    '''
    with open(json_in) as f:
        grouped = json.load(f)
    language = dict_to_language(grouped)
    with open(language_out, 'wb') as f:
        f.write(language.SerializeToString())


if __name__ == '__main__':
    parsable.dispatch()
