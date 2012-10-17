#from language_pb2 import Language, WeightedTerm
from language_pb2 import *


def dict_to_language(dict_):
    lang = Langauge()
    for key, val in dict_.iteritems():
        term = lang.terms.add()
        term.name = key
        term.prob = val
    return lang
