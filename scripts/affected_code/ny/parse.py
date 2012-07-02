import re
from functools import partial, wraps
import logging
import pprint
import sys


logger = logging.getLogger('code-parser')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


#'NYB00008280'
def main():
    print 1
    with open(sys.argv[1]) as f:

        text = f.read()

        # Slice beginning crap.
        _, text = text.split('DO ENACT AS FOLLOWS:')

        # Kill line numbers.
        text = re.sub(r' {3,4}\d+ {2}', '', text)

        paragraphs = []
        text = iter(text.splitlines())
        lines = []
        while True:
            try:
                line = next(text)
            except StopIteration:
                paragraphs.append(' '.join(lines))
                break

            lines.append(line)
            if len(line) != 72:
                paragraphs.append(' '.join(lines))
                lines = []

        def filterfunc(s):
            return (not (s.isupper() or ('shall take effect' in s)) \
                    and (re.search(r'^  Section +1.', s) or \
                         re.search(r'^  S {1,2}\d+', s)))

        paragraphs = filter(filterfunc, paragraphs)
        paragraphs = map(partial(re.sub, r'\s+', ' '), paragraphs)
        pprint.pprint(paragraphs)
        for p in paragraphs:
            print p
            toks = list(ParagraphLexer().get_tokens_unprocessed(p))
            pprint.pprint(toks)
            Parser(toks).parse()
            import pdb;pdb.set_trace()
        return paragraphs


from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

SectionID = Token.Section.ID
NodeType = Token.Node.Type
NodeID = Token.Node.ID
ActionVerb = Token.Action.Verb
ActionInfo = Token.Action.Info
ActName = Token.ActName
CompilationName = Token.CompilationName


class ParagraphLexer(RegexLexer):

    tokens = {
        'root': [
            (r' +Section (1).\s+', bygroups(SectionID)),
            (r' {1,2}S {1,2}(\d+)\.', bygroups(SectionID)),
            (r',? .{,50}as (?:added|amended) by[^,]+?, ', Token.Error),
            (r'(?i)(paragraph|subsection|section|chapter|subdivision|clause|the laws of) ([^ ,]+)( of )?',
                bygroups(NodeType, NodeID)),
            (r', constituting (.{,250}) act,', Token.ActName),
            (r'(?i)the ([A-Za-z .&]+ (:?law|rules|code of the city of New York))', bygroups(Token.CompilationName)),

            (r'is (amended|repealed)', bygroups(ActionVerb)),
            (r'by (add)ing \S+ new ', bygroups(ActionInfo)),
            (r' to read as follows:', Token.Error),
            ],
    }


def token_to_key(token):
    return token[-1].lower()


class Parser(object):

    def __init__(self, tokens):
        self.ignored_token_types = [Token.Error]
        self.tokens = iter(tokens)

        self._sections = []
        self._current_section = None
        self._current_node = None

        functions = {}
        for k, v in self.__class__.__dict__.items():
            if hasattr(v, 'on_token'):
                functions[v.on_token] = v

        self.functions = functions

    def on_token(token, expected=None):
        def wrapper(f):
            @wraps(f)
            def wrapped(self, pos, token, text, *args, **kwargs):
                f(self, pos, token, text, *args, **kwargs)
                return expected
            wrapped.on_token = token
            return wrapped
        return wrapper

    def get_function_by_token(self, token):
        try:
            return self.functions[token]
        except KeyError:
            pprint.pprint(self.functions)
            print token, repr(token)
            import pdb;pdb.set_trace()
            raise

    def parse(self):
        expected = []
        while True:
            try:
                data = pos, token, text = self.expect(expected)
            except StopIteration:
                break
            else:
                func = self.get_function_by_token(token)
                logger.debug('doing %r on %r' % (func, token))
                expected = func(self, *data)

        self.finalize()
        return self._sections

    def finalize(self):
        '''Last stuff before done.
        '''
        # import pprint
        # pprint.pprint(self._sections)

    def expect(self, expected=[]):
        '''Return a token of the expected type or complain.
        '''
        ignored_token_types = self.ignored_token_types
        if len(expected) == 0:
            data = pos, _token, text = next(self.tokens)

        else:
            data = pos, _token, text = next(self.tokens)
            if _token in ignored_token_types:
                return self.expect(expected)

            if _token not in expected:
                msg = 'Expected one of %r, got %r.'
                raise ValueError(msg % (expected, _token))

        self.current_pos = pos
        self.current_text = text
        self.current_token = _token
        self.current_data = data

        return data

    # Node access.
    def _new_node(self):
        node = {}
        self.current_section['nodes'].append(node)
        self._current_node = node
        return node

    @property
    def current_node(self):
        if self._current_node is None:
            return self._new_node()
        else:
            return self._current_node

    def close_node(self):
        self._current_node = None

    # Section access.
    def _new_section(self):
        section = {'nodes': []}
        self._sections.append(section)
        self._current_section = section
        return section

    @property
    def current_section(self):
        if self._current_section is None:
            return self._new_section()
        else:
            return self._current_section

    def close_section(self):
        self._current_section = None

    # -----------------
    # Parser functions.
    @on_token(SectionID, expected=[NodeType, CompilationName])
    def section_id(self, pos, token, text):
        key = token_to_key(token)
        self.current_section[key] = text

    @on_token(NodeType, expected=[NodeID, CompilationName])
    def node_type(self, pos, token, text):
        key = token_to_key(token)
        text = text.lower()
        if token in self.current_node:
            self.close_node()
        self.current_node[key] = text

    @on_token(NodeID, expected=[NodeType, CompilationName])
    def node_ID(self, pos, token, text):
        key = token_to_key(token)
        if token in self.current_node:
            self.close_node()
        self.current_node[key] = text

    @on_token(CompilationName, expected=[NodeType, ActionVerb])
    def compilation(self, pos, token, text):
        section = self.current_section
        section['type'] = 'statute'
        section['id'] = text

    @on_token(ActionInfo, expected=[ActionVerb])
    def action_descriptor(self, pos, token, text):
        key = token_to_key(token)
        self.current_section[key] = text

    @on_token(ActionVerb, expected=[NodeType])
    def action_type(self, pos, token, text):
        key = token_to_key(token)
        self.current_section[key] = text


def sanitize(s):
    return re.sub(r'(?: as )?[a-z]+ed by .+?,( is (?:amended|renumbered|repealed))',
                  lambda m: m.group(1), s, re.S)


def parse(string):
    sanitized = sanitize(string)
    tokens = ParagraphLexer().get_tokens_unprocessed(sanitized)
    parsed = Parser(tokens).parse()
    return parsed


def main1():
    import sys
    index = int(sys.argv[1])

    def sanitize(s):
        return re.sub(r'(?: as )?[a-z]+ed by .+?,( is (?:amended|renumbered|repealed))',
                      lambda m: m.group(1), s, re.S)
    import nytests
    samples = nytests.samples

    text = samples[index][0]
    sanitized = sanitize(text)
    print text
    print '----------------'
    print sanitized
    toks = list(ParagraphLexer().get_tokens_unprocessed(sanitized))
    pprint.pprint(toks)
    Parser(toks).parse()


    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main1()
