import simplejson as json
from pomagma.language import dict_to_language
import parsable


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
