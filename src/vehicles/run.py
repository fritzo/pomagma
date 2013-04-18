import simplejson as json
from pomagma.vehicles.vehicles_pb2 import Vehicle, WeightedTerm
import parsable


arity_map = {
    'NULLARY': WeightedTerm.NULLARY,
    'INJECTIVE': WeightedTerm.INJECTIVE,
    'BINARY': WeightedTerm.BINARY,
    'SYMMETRIC': WeightedTerm.SYMMETRIC,
    }


@parsable.command
def compile(json_in, vehicle_out):
    '''
    Convert vehicle from json to protobuf format
    '''
    with open(json_in) as f:
        grouped = json.load(f)

    total = sum(weight for _, group in grouped.iteritems()
                       for _, weight in group.iteritems())
    assert total > 0, "total weight is zero"
    scale = 1.0 / total

    vehicle = Vehicle()
    for arity, group in grouped.iteritems():
        for name, weight in group.iteritems():
            term = vehicle.terms.add()
            term.name = name
            term.arity = arity_map[arity.upper()]
            term.weight = scale * weight

    with open(vehicle_out, 'wb') as f:
        f.write(vehicle.SerializeToString())


if __name__ == '__main__':
    parsable.dispatch()
