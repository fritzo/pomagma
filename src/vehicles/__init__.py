#from vehicles_pb2 import Vehicle, WeightedTerm
from pomagma.vehicles.vehicles_pb2 import Vehicle


def dict_to_vehicle(dict_):
    lang = Vehicle()
    total = sum(dict_.values())
    scale = 1.0 / total
    for key, val in dict_.iteritems():
        term = lang.terms.add()
        term.name = key
        term.weight = scale / total
    return lang
