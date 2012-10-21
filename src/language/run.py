import simplejson as json
from pomagma.language.language_pb2 import Language, WeightedTerm
import parsable


arity_map = {
    'NULLARY': WeightedTerm.NULLARY,
    'INJECTIVE': WeightedTerm.INJECTIVE,
    'BINARY': WeightedTerm.BINARY,
    'SYMMETRIC': WeightedTerm.SYMMETRIC,
    }


@parsable.command
def compile(json_in, language_out):
    '''
    Convert language from json to protobuf format
    '''
    with open(json_in) as f:
        grouped = json.load(f)

    total = sum(weight for _, group in grouped.iteritems()
                       for _, weight in group.iteritems())
    assert total > 0, "total weight is zero"
    scale = 1.0 / total

    language = Language()
    for arity, group in grouped.iteritems():
        for name, weight in group.iteritems():
            term = language.terms.add()
            term.name = name
            term.arity = arity_map[arity.upper()]
            term.weight = scale * weight

    with open(language_out, 'wb') as f:
        f.write(language.SerializeToString())


if __name__ == '__main__':
    parsable.dispatch()
