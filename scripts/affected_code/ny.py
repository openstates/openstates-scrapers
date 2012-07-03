import copy

from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

import base


SectionID = Token.Section.ID
NodeType = Token.Node.Type
NodeID = Token.Node.ID
NodeAndOrComma = Token.Node.AndOrComma
AmendedAsFollows = Token.AmendedAsFollows
AmendedByAdding = Token.AmendedByAdding
Renumbered = Token.Renumbered
SessionLawChapter = Token.SessionLawChapter
SessionLawYear = Token.SessionLawYear
ActName = Token.ActName
CompilationName = Token.CompilationName
Junk = Token.Junk

subds = ['paragraph', 'division', 'chapter', 'section', 'clause']
subds += ['sub' + s for s in subds]
subds = r'(%s)s?' % '|'.join(sorted(subds, key=len, reverse=True))


class Lexer(RegexLexer):

    tokens = {
        'root': [
            (r' +Section (1).\s+', bygroups(SectionID)),
            (r' {1,2}S {1,2}(\d+)\.', bygroups(SectionID)),
            (r'(?i)(?: of (?:a )?)?(%s) ' % subds,
                bygroups(NodeType), 'path'),
            (r', constituting the (.{,250}? act),', bygroups(ActName)),
            (r' (is|are) amended to read as follows:', AmendedAsFollows),
            (r' is amended by adding', AmendedByAdding, 'path'),
            (r' is renumbered', Renumbered),
            (r'amended to read as follows:', AmendedAsFollows),
            (r'amended by adding', AmendedByAdding, 'path'),
            (r'renumbered', Renumbered),

            # Junk.
            (r'as (added|amended|renumbered) [^,]+', Junk, 'junk'),
            (r'(added|amended|renumbered) [^,]+', Junk, 'junk'),
            (r'%s .{,200}? as (?:added|amended) by[^,]+?, ' % subds, Token.Junk),
            ],

        'path': [
            (r' of the laws of (\d{4})', bygroups(SessionLawYear), '#pop'),
            (r'(?i)of the ([A-Za-z .&]+ (:?law|rules|code of the city of New York))',
             bygroups(CompilationName), '#pop'),
            (r'(?i)(?: of (?:a )?)?(%s) ' % subds,
                bygroups(NodeType)),
            (r'[^ ,]+', NodeID),
            (r', ', NodeAndOrComma),
            (r' and ', NodeAndOrComma),
            ],

        'junk': [
            (r'(?!(is|are) (amended|renumbered|repealed)).', Junk),
            (r'(is|are) amended to read as follows:', AmendedAsFollows, '#pop'),
            (r'is amended by adding', AmendedByAdding, '#pop'),
            (r'is renumbered', Renumbered, '#pop'),
            ]
    }


class ParserState(dict):

    def __init__(self):
        self._current_path = None
        self._current_node = None
        self['paths'] = []

    def finalize(self):
        return dict(self)

    def path_new(self, text=None, *args, **kwargs):
        path = []
        self['paths'].append(path)
        self._current_path = path
        return path

    @property
    def path_current(self, text=None, *args, **kwargs):
        if self._current_path is None:
            return self._new_path()
        else:
            return self._current_path

    def node_new(self, text=None, *args, **kwargs):
        node = {}
        self.path_current.append(node)
        self._current_node = node
        return node

    @property
    def node_current(self, text=None, *args, **kwargs):
        if self._current_node is None:
            return self._new_node()
        else:
            return self._current_node

    def node_set_id(self, text=None, *args, **kwargs):
        text = text.rstrip('.')
        self.node_current['id'] = text

    def node_set_type(self, text=None, *args, **kwargs):
        text = text.lower().rstrip('s')
        node_current = self.node_current
        if 'type' not in node_current:
            node_current['type'] = text
        else:
            self.node_new()['type'] = text

    def path_clone(self, text=None, *args, **kwargs):
        new_path = copy.deepcopy(self.path_current)
        self['paths'].append(new_path)
        self._current_path = new_path
        self._current_node = new_path[-1]
        return new_path

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

    def amendment_adding(self, text=None, *args, **kwargs):
        paths = []
        path = []
        node = self.node_new()
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


class Parser(base.Parser):

    ignored_token_types = [Token.Error]

    rules = {
        'root': [
            (NodeType, 'path_new node_new node_set_type', 'path'),
            (AmendedAsFollows, 'amended_as_follows'),
            (AmendedByAdding, '', 'amended_by_adding'),
            (Renumbered, 'renumbered', 'path'),
            (ActName, 'path_set_act_name'),
            (Junk, ''),
            ],

        'path': [
            (SessionLawYear, 'path_set_session_law_year', '#pop'),
            (CompilationName, 'path_set_compilation_name', '#pop'),
            (NodeID, 'node_set_id'),
            (NodeType, 'node_set_type'),
            (NodeAndOrComma, 'path_clone'),
            ],

        'amended_by_adding': [
            (AmendedByAdding, 'amendment_adding', 'path'),
            ],
        }
