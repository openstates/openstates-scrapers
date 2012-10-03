from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import *

from .base import parser
from . import enumerations

t = Token

print enumerations.regex


class Lexer(RegexLexer):

    tokens = {
        'root': [
            include('impact'),
            include('_conjunctions'),
            include('nodetypes'),
            include('junk'),
            (r'(?i)present', t.Present),
            (r'of ', t.Of),
            (r'(?i)respectively', t.Respectively),
            include('junk'),
            ],

        'impact': [
            (r'(?:are|is) (creat|amend|renumber|add|repeal)ed( to )?',
                bygroups(t.ImpactVerb)),
            ],

        'nodetypes': [

            (r'(?i)Section\s+([^ ,]+), (Florida Statutes),',
                bygroups(t.SectionEnum, t.Code)),

            # Match plural path elements.
            (r'(?i)%ss ' % enumerations.regex,
                bygroups(t.NodeType.Plural), 'path'),

            (r'chapter (\s+), Laws of Florida', bygroups(t.ChapterLaw)),

            # Match singular path elements.
            (r'(?i)%s' % enumerations.regex, bygroups(t.NodeType), 'path'),
            ],

        'path': [
            include('impact'),
            include('_conjunctions'),
            include('nodetypes'),
            include('junk'),
            (r'(?i)respectively', t.Respectively, '#pop'),
            (r'(?i)a new', t.New, '#pop'),
            (r'of ', t.Of, '#pop'),
            (r'(?i)(that) (%s)' % enumerations.regex,
                bygroups(t.That, t.NodeType), '#pop'),
            (r'through', t.NodeSpan),
            include('impact'),
            include('_conjunctions'),
            include('nodetypes'),
            (r'\(?([^ \),]+)\)?', bygroups(t.NodeEnum)),
            ],

        '_conjunctions': [
            (r',? and ', t.And),
            (r', ', t.Comma),
            ],

        'junk': [
            (r'to read:', t.Error),
            (r'read:', t.Error),
            ]
    }


class Stream(parser.Stream):
    filters = [lambda token: token.tokentype != Token.Error]


class Parser(parser.Parser):

    stream_cls = Stream

    def parse(self):

        # Section 1003.46, Florida Statutes, is amended to read:
        while True:

            if self.stream.exhausted:
                break

            section_code_verb = self.expect_seq(t.SectionEnum, t.Code, t.ImpactVerb)
            with section_code_verb as tokens:
                if tokens:
                    section_enum, code, impact = tokens
                    self.state['loc']['section_enum'] = section_enum.text
                    self.state['loc']['code'] = 'stat'
                    self.state['loc']['impact_verb'] = impact.text
                    continue

            # Paragraph (d) of subsection (3) of section 1002.20...:
            node_path = self.expect_seq(t.NodeType, t.NodeEnum,
                                        repeat=True, ignore=[t.Of])
            with node_path as tokens:
                if tokens:
                    self.state['loc'].add_path(reversed(tokens))
                    continue

            nodetype_plural = self.expect_one(t.NodeType.Plural)

            node_series = self.expect_seq(t.NodeEnum, repeat=True, flat=True,
                                          ignore=[t.Comma, t.And])
            node_path = self.expect_seq(t.NodeType, t.NodeEnum,
                                        repeat=True, ignore=[t.Of])
            with nodetype_plural as nodetype, node_series as tokens, \
                    self.expect_one(t.Of) as of, node_path as path:
                    if nodetype and tokens and of and path:
                        a = 1
                        import pdb;pdb.set_trace()
                        b = 2
                        continue

            nodetype_plural = self.expect_one(t.NodeType.Plural)

            node_series = self.expect_seq(t.NodeEnum, repeat=True, flat=True,
                                          ignore=[t.Comma, t.And])
            with nodetype_plural as nodetype, node_series as tokens:
                if tokens or nodetype:
                    self.state['loc'].add_parallel_nodes(nodetype, tokens)
                    continue

            try:
                self.stream.next()
            except StopIteration:
                break
