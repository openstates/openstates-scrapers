import os
from os.path import join
import pprint

from pygments.token import *

from billy.conf import settings


def get_billtext(abbr):
    '''A generator of billtext for the given state.
    '''
    DATA = join(settings.BILLY_DATA_DIR, abbr, 'billtext')
    for filename in os.listdir(DATA):
        filename = join(DATA, filename)
        with open(filename) as f:
            text = f.read()
        yield filename, text


def parse(lexer_class, parser_class, parser_state, string):
    print string
    tokens = list(lexer_class().get_tokens_unprocessed(string))
    pprint.pprint(tokens)
    # return tokens
    parser = parser_class(tokens, parser_state)
    parser.parse()
    result = parser.state['loc'].finalize()
    pprint.pprint(result)
    import pdb;pdb.set_trace()
