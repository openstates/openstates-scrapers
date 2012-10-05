import collections
import contextlib
import itertools

from pygments.token import *
import logbook

from .location import LocationSpec


LEVEL = 0
logger = logbook.Logger('parser', level=LEVEL)


class ParseError(Exception):
    pass


Token = collections.namedtuple('Token', 'pos tokentype text')


class Stream(object):

    def __init__(self, iterable, filters=[], reverse=None):

        # Wrap tokens in Token class.
        stream = map(Token._make, iterable)

        # Filter junk from the stream.
        filters = getattr(self, 'filters', filters)
        for func in filters:
            stream = filter(func, stream)

        # Reverse the tokens if necessary.
        if reverse is None:
            reverse = getattr(self, 'reverse', False)
            if reverse:
                stream = stream[::-1]

        self.i = 0
        self.last = len(stream)
        self._stream = stream

    def __iter__(self):
        while True:
            try:
                yield self._stream[self.i]
            except IndexError:
                raise StopIteration
            finally:
                self.i += 1

    def __repr__(self):
        return 'Stream(i=%r, %r)' % (self.i, self._stream)

    def next(self):
        if self.exhausted:
            raise StopIteration
        try:
            return self._stream[self.i]
        except IndexError:
            raise StopIteration
        finally:
            self.i += 1

    def previous(self):
        return self.behind(1)

    def this(self):
        try:
            return self._stream[self.i]
        except IndexError:
            raise StopIteration

    def ahead(self, n=1):
        try:
            return self._stream[self.i + n]
        except IndexError:
            return

    def behind(self, n=1):
        i = self.i - 1
        if i < 0:
            return
        try:
            return self._stream[i]
        except IndexError:
            return

    @property
    def exhausted(self):
        '''Stream iterator is through? Yep/nope
        '''
        return self.last <= self.i


class Parser(object):

    class SequenceMismatch(ParseError):
        '''Raised if expected sequence differs from
        actual sequence found.
        '''

    def __init__(self, tokenstream, parser_state=None):

        # Apply stream class.
        if not isinstance(tokenstream, (Stream,)):
            stream_cls = getattr(self, 'stream_cls', Stream)
            tokenstream = stream_cls(tokenstream)
        self.stream = tokenstream

        if parser_state is not None:
            self.state = parser_state()
        else:
            self.state = ParserState()
        self._compile_rules()

    def _compile_rules(self):
        if not hasattr(self, 'rules'):
            return
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

    def _take_tokentype_sequence(self, sequence, repeat=False,
            flat=False, ignore=None):
        '''Return tokens from the stream if they match the given sequence.
        '''
        result = []
        repeat_sequence = repeat
        repeat_result = []
        ignored_tokentypes = ignore or []
        while True:
            _sequence = list(sequence[::-1])
            while _sequence:
                expected_type = _sequence.pop()
                logger.debug('  expected_type: %r' % expected_type)
                while True:
                    try:
                        token = self.stream.next()
                    except StopIteration:
                        raise self.SequenceMismatch('Reached end of stream.')
                    if token.tokentype not in ignored_tokentypes:
                        logger.debug('  found: %r' % (token,))
                        break
                    logger.debug('  ignoring: %r' % (token,))
                if token.tokentype == expected_type:
                    result.append(token)
                else:
                    msg = '  bailing (wrong tokentype): %r'
                    logger.debug(msg % [token])
                    if repeat_sequence is False:
                        raise self.SequenceMismatch('Seqs didn\'t match.')
                    elif repeat_result:
                        # Manually roll-back the stream index 1 position.
                        self.stream.i -= 1
                        if flat:
                            return _flatten(repeat_result)
                        return repeat_result
                    else:
                        raise self.SequenceMismatch('Seqs didn\'t match.')

            if repeat_sequence is False:
                return result
            else:
                repeat_result.append(result)
                result = []
        if flat:
            return _flatten(repeat_result)
        return repeat_result

    @contextlib.contextmanager
    def expect_seq(self, *tokentypes, **kwargs):
        '''Look ahead into the stream, and if the tokens found match
        the given tokentype sequence, yield; otherwise, return.
        '''
        i = self.stream.i
        try:
            logger.debug('expect_seq: *%r' % (tokentypes,))
            yield self._take_tokentype_sequence(tokentypes, **kwargs)
        except self.SequenceMismatch:
            # Reset the stream position.
            logger.debug('failed: expect_seq: *%r' % (tokentypes,))
            logger.debug('reseting stream index to %d' % i)
            self.stream.i = i
            yield

    @contextlib.contextmanager
    def expect_one(self, tokentype):
        '''Look ahead into the stream, and if the tokens found match
        the given tokentype sequence, yield; otherwise, return.
        '''
        logger.debug('expect_one: %r' % [tokentype])
        token = self.stream.this()
        logger.debug('  found: %r' % [token])
        if token.tokentype == tokentype:
            yield self.stream.next()
        else:
            logger.debug('failed: expect_one: %r' % [tokentype])
            yield

    # @contextlib.contextmanager
    # def expect_subnode_series(self):
    #     i = self.stream.i

    #     seq = (Token.NodeType, Token.NodeEnum)
    #     try:
    #         yield self._take_tokentype_sequence(tokentypes, **kwargs)
    #     except self.SequenceMismatch:
    #         # Reset the stream position.
    #         self.stream.i = i
    #         yield


class ParserState(dict):

    def __init__(self):

        # The location spec.
        self['loc'] = LocationSpec()

    def validate(self):
        '''Check that all the required attrs have been
        added; raise errors if not.
        '''
        required_keys = set(['rsrc', 'loc'])
        undefined_keys = set(required_keys) - set(self)
        if undefined_keys:
            msg = ("The following keys are required but weren't ",
                   "added during the parse: %r")
            raise ParseError(msg % undefined_keys)

    def finalize(self):
        return dict(self)

    def path_set_compilation_name(self, text=None, *args, **kwargs):
        self['type'] = 'statute'
        self['id'] = text

    def path_set_session_law_year(self, text=None, *args, **kwargs):
        self['type'] = 'session_law'
        self['year'] = text

    def path_set_session_law_chapter(self, text=None, *args, **kwargs):
        self['type'] = 'session_law'
        self['chapter'] = text

    def path_set_act_name(self, text=None, *args, **kwargs):
        self['act_name'] = text.strip(', ')

    def amended_by_adding(self, text=None, *args, **kwargs):
        paths = []
        path = []
        node = {}
        path.append(node)
        paths.append(path)
        self._current_node = node
        self._current_path = path
        self['impact'] = 'added'
        self['details'] = paths

    def amended_as_follows(self, text=None, *args, **kwargs):
        self['impact'] = 'amended'

    def renumbered(self, text=None, *args, **kwargs):
        paths = []
        path = []
        node = {}
        path.append(node)
        paths.append(path)
        self._current_node = node
        self._current_path = path
        self['impact'] = 'renumbered'
        self['details'] = paths


def parse(string):
    tokens = ParagraphLexer().get_tokens_unprocessed(string)
    parsed = Parser(tokens).parse()
    return parsed


def _flatten(iterable):
    return list(itertools.chain.from_iterable(iterable))
