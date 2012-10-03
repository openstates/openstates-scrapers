import copy

from pygments.lexer import RegexLexer, bygroups
from pygments.token import *

import .base


SectionID = Token.Section.ID
NodeType = Token.Node.Type
NodeID = Token.Node.ID
NodeAndOrComma = Token.Node.AndOrComma
DiffSpec = Token.DiffSpec
AmendedAsFollows = DiffSpec.AmendedAsFollows
AmendedByAdding = DiffSpec.AmendedByAdding
Renumbered = DiffSpec.Renumbered
SessionLawChapter = Token.SessionLawChapter
SessionLawYear = Token.SessionLawYear
ActName = Token.ActName
CompilationName = Token.CompilationName
Junk = Token.Junk

subds = ['paragraph', 'division', 'chapter', 'section', 'clause',
         'article', 'part']
subds += ['sub' + s for s in subds]
subds = r'(%s)' % '|'.join(sorted(subds, key=len, reverse=True))


class Lexer(RegexLexer):

    tokens = {
        'root': [

            # Match 'Section 1' and 'S 2' section headings.
            (r' +Section (1).\s+', bygroups(SectionID)),
            (r' {1,2}S {1,2}(\d+)\.', bygroups(SectionID)),

            # Match singular path elements.
            (r'(?i)(?: of (?:a )?)?(%s) ' % subds,
                bygroups(NodeType), 'path'),

            # Match plural path elements.
            (r'(?i)(%s)s ' % subds, bygroups(NodeType.Plural), 'path'),

            # Match act name.
            (r', constituting the (.{,250}? act),', bygroups(ActName)),

            # Amended as follows variants.
            (r' (is|are) amended to read as follows:', AmendedAsFollows),
            (r'amended to read as follows:', AmendedAsFollows),

            # Amended by adding variants.
            (r' (is|are) amended and \w+ new', AmendedByAdding, 'path'),
            (r' is amended by adding', AmendedByAdding, 'path'),
            (r'amended by adding', AmendedByAdding, 'path'),


            # Compilation name.
            (r'(?i)the ([A-Za-z .&]+ (:?law|rules|code of the city of New York))',
             bygroups(CompilationName)),

            (r'(added|amended|renumbered) by',
            # (r',? (:?(:?as|and) )?(added|amended|renumbered) by',
                Token.RevisionSpec, 'path'),
            # Junk.
            # (r'amending [^,]+', Junk, 'junk'),
            # (r'(added|amended|renumbered) [^,]+', Junk, 'junk'),
            # (r'%s .{,200}? as (?:added|amended) by[^,]+?, ' % subds, Token.Junk),
            # Renumbered variants.
            (r' is renumbered', Renumbered),
            (r'renumbered', Renumbered),
            (r'\band\b', Token.And)
            ],

        'path': [
            (r',? (:?(:?as|and) )?(added|amended|renumbered) by', Token.RevisionSpec),

            (r' local law number (\w+) of the city of (.+?) for the year (\w+)',
                bygroups(Token.LocalLaw.Number,
                         Token.LocalLaw.Jxn,
                         Token.LocalLaw.Year), '#pop'),

            (r' local law number (\w+)',
                bygroups(Token.LocalLaw.Number), '#pop'),

            # "of the codes and ordinances of the city of Yonkers..."
            (r' of the (.+?) of the city of (.+?)(?:,|is)',
                bygroups(Token.MunicipalLaw.Name, Token.MunicipalLaw.Jxn), '#pop'),

            (r' of the laws of (\d{4})', bygroups(SessionLawYear), '#pop'),
            (r'(?i)of the ([A-Za-z \-.&]+ (:?law|rules|code of the city of New York))',
             bygroups(CompilationName), '#pop'),
            (r'(?i)(?: of (?:a )?)?(%s) ' % subds,
                bygroups(NodeType)),
            (r'are added', Token.Added, '#pop'),
            (r'to read as follows', Junk, '#pop'),
            (r'of ', Token.Of, '#pop'),
            (r'[^ ,]+', NodeID),
            (r',? and ', NodeAndOrComma),
            (r', ', NodeAndOrComma),
            ],

        'junk': [
            (r'(?!(is|are) (amended|renumbered|repealed)).', Junk),
            (r'(is|are) amended to read as follows:', AmendedAsFollows, '#pop'),
            (r' (is|are) amended and \w+ new', AmendedByAdding, 'path'),
            (r' is amended by adding', AmendedByAdding, '#pop'),
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

    def section_set_id(self, text=None, *args, **kwargs):
        self['section'] = text

    def path_new(self, text=None, *args, **kwargs):
        path = []
        self['paths'].append(path)
        self._current_path = path
        return path

    @property
    def path_current(self, text=None, *args, **kwargs):
        if self._current_path is None:
            return self.path_new()
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


class Parser(base.Parser):

    ignored_token_types = [Token.Error]

    rules = {
        'root': [
            (SectionID, 'section_set_id'),
            (NodeType, 'path_new node_new node_set_type', 'path'),
            (NodeType.Plural, 'path_new_parallel node_new node_set_type', 'path'),
            (AmendedAsFollows, 'amended_as_follows'),
            (AmendedByAdding, 'amended_by_adding', 'path'),
            (Renumbered, 'renumbered', 'path'),
            (ActName, 'path_set_act_name'),
            (Junk, ''),
            (CompilationName, 'path_set_compilation_name'),
            ],

        'path': [
            (SessionLawYear, 'path_set_session_law_year', '#pop'),
            (CompilationName, 'path_set_compilation_name', '#pop'),
            (NodeID, 'node_set_id'),
            (NodeType, 'node_set_type'),
            (NodeAndOrComma, 'path_clone'),
            (Junk, '', '#pop')
            ],
        }
