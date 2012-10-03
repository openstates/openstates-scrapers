from operator import getitem
from collections import defaultdict


class DefaultdictNode(defaultdict):
    '''A default dict that allows setattr, since
    it needs a `parent` attribute.
    '''
    pass


class LocationSpec(defaultdict):
    '''Basically a recursive defaultdict with helper methods.'''

    def __init__(self, *args, **kwargs):
        super(LocationSpec, self).__init__(*args, **kwargs)
        self.current_node = self
        self._nodetypes = defaultdict(list)

    def __missing__(self, k):
        f = lambda: DefaultdictNode(f)
        res = DefaultdictNode(f)

        # Set self as parent for future reference.
        res.parent = self
        self[k] = res
        return res

    def _setkeys(self, value, *keys):
        keys = list(keys)
        lastkey = keys.pop()
        node = reduce(getitem, [self] + list(keys))
        node[lastkey] = value
        self.current_node = node

    def _getkeys(self, *keys):
        node = reduce(getitem, [self] + list(keys))
        self.current_node = node
        return node

    def _get_recent_nodetype(self, nodetype):
        nodetype = nodetype.lower()
        nodetype = self._nodetypes[nodetype]
        if nodetype:
            # Got most recently added node for this type.
            return nodetype[-1].parent
        else:
            return self

    def _log_node(self, nodetype, child):
        self._nodetypes[nodetype.text.lower()].append(child)

    def add_parallel_nodes(self, nodetype, tokens):
        '''Add tokens containing nodenum information into the
        tree hierarchy of the statute. Log added nodes in the
        _nodetypes dict.
        '''
        node = self._get_recent_nodetype(nodetype.text)
        for token in tokens:
            child = node[token.text]
            self._log_node(nodetype, child)

    def add_path(self, tokens):
        '''Where tokens is a sequence of (nodetype, node_enum) 2-tuples.
        '''
        tokens = list(tokens)
        nodetype, node_enum = tokens[0]
        node = self._get_recent_nodetype(nodetype.text)
        for nodetype, node_enum in tokens:
            node = node[node_enum.text]
            self._log_node(nodetype, node)

    def finalize(self):
        terminal_value = self['impact_verb']

        def _convert_to_dict(_defaultdict, terminal_value=terminal_value):
            res = {}
            for k, v in _defaultdict.items():
                if v:
                    if isinstance(v, dict):
                        res[k] = _convert_to_dict(v)
                    else:
                        res[k] = v
                else:
                    res[k] = terminal_value
            return res

        return _convert_to_dict(self)
