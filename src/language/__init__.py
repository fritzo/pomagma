#from language_pb2 import Language, WeightedTerm
from pomagma.language.language_pb2 import Language


def dict_to_language(dict_):
    lang = Language()
    total = sum(dict_.values())
    scale = 1.0 / total
    for key, val in dict_.iteritems():
        term = lang.terms.add()
        term.name = key
        term.weight = scale / total
    return lang
