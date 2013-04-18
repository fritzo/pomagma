import simplejson as json
from pomagma.vehicles import dict_to_vehicle
import parsable


@parsable.command
def compile(json_in, vehicle_out):
    '''
    Convert vehicle from json to protobuf format.
    '''
    with open(json_in) as f:
        grouped = json.load(f)
    vehicle = dict_to_vehicle(grouped)
    with open(vehicle_out, 'wb') as f:
        f.write(vehicle.SerializeToString())


if __name__ == '__main__':
    parsable.dispatch()
