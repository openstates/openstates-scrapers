from pygments.token import *
import logbook

LEVEL = logbook.ERROR
logger = logbook.Logger('parse', level=LEVEL)


class ParseError(Exception):
    pass


class Parser(object):

    def __init__(self, tokenstream, parser_state):
        self.stream = tokenstream
        self._parser_state = parser_state()
        self._compile_rules()

    def _compile_rules(self):
        compiled_rules = {}
        parser_state = self._parser_state
        for state, state_rules in self.rules.items():
            compiled_state_rules = {}
            for data in state_rules:
                states = None
                len_data = len(data)
                if len_data == 3:
                    token, func_names, states = data
                elif len_data == 2:
                    token, func_names = data
                funcs = [getattr(parser_state, f) for f in func_names.split()]
                compiled_state_rules[token] = {'funcs': funcs}
                if states is not None:
                    compiled_state_rules[token]['states'] = states
                compiled_rules[state] = compiled_state_rules
        self._rules = compiled_rules

    def parse(self):
        rules = self._rules
        state_stack = []
        ignored_token_types = self.ignored_token_types

        for pos, token, text in self.stream:
            logger.debug('data: %r' % [pos, token, text])

            if token in ignored_token_types:
                logger.debug('ignoring %r %r' % (token, text))
                continue

            try:
                state = state_stack[-1]
            except IndexError:
                state = 'root'
            logger.debug('entering state: %r' % state)

            state_rules = rules[state][token]

            while True:
                try:
                    funcs = state_rules['funcs']
                except KeyError:
                    if state_stack:
                        state = state_stack.pop()
                        logger.debug('pop state: %r' % state)
                    else:
                        msg = 'No rules available for %r in state %r.'
                        raise ParseError(msg % (token, state))
                else:
                    for f in funcs:
                        logger.debug('calling %r(%r)' % (f, text))
                        f(text)
                    break

            if 'states' in state_rules:
                _states = state_rules['states']
                if isinstance(_states, basestring):
                    _states = [_states]
                for st in _states:
                    if st == '#pop':
                        logger.debug('pop state: %r' % state_stack[-1])
                        state_stack.pop()
                    else:
                        logger.debug('push state: %r' % st)
                        state_stack.append(st)

        return dict(self._parser_state)


def parse(string):
    tokens = ParagraphLexer().get_tokens_unprocessed(string)
    parsed = Parser(tokens).parse()
    return parsed
