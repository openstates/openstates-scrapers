import re
from collections import namedtuple, defaultdict, Iterable
from six import string_types


class Rule(namedtuple("Rule", "regexes types stop attrs")):
    """If any of ``regexes`` matches the action text, the resulting
    action's types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    """

    def __new__(
        _cls, regexes, types=None, stop=False, flexible_whitespace=True, **kwargs
    ):
        "Create new instance of Rule(regex, types, attrs, stop)"

        # Regexes can be a string, regex, or sequence.
        if isinstance(regexes, string_types) or hasattr(regexes, "match"):
            regexes = (regexes,)
        compiled_regexes = []
        # pre-compile any string regexes
        for regex in regexes:
            if isinstance(regex, string_types):
                if flexible_whitespace:
                    regex = re.sub(r"\s{1,4}", r"\\s{,10}", regex)
                compiled_regexes.append(re.compile(regex))
            else:
                compiled_regexes.append(regex)

        # Types can be a string or a sequence.
        if isinstance(types, string_types):
            types = set([types])
        types = set(types or [])

        return tuple.__new__(_cls, (compiled_regexes, types, stop, kwargs))

    def match(self, text):
        attrs = {}
        matched = False

        for regex in self.regexes:
            m = regex.search(text)
            if m:
                matched = True
                # add any matched attrs
                attrs.update(m.groupdict())

        if matched:
            return attrs
        else:
            # return None if no regexes matched
            return None


class BaseCategorizer(object):
    """A class that exposes a main categorizer function
    and before and after hooks, in case categorization requires specific
    steps that make use of action or category info. The return
    value is a 2-tuple of category types and a dictionary of
    attributes to overwrite on the target action object.
    """

    rules = []

    def __init__(self):
        pass

    def categorize(self, text):
        # run pre-categorization hook on text
        text = self.pre_categorize(text)

        types = set()
        return_val = defaultdict(set)

        for rule in self.rules:

            attrs = rule.match(text)

            # matched if attrs is not None - empty attr dict means a match
            if attrs is not None:
                # add types, rule attrs and matched attrs
                types |= rule.types

                # Also add its specified attrs.
                for k, v in attrs.items():
                    return_val[k].add(v)

                return_val.update(**rule.attrs)

                # break if there was a match and rule says so, otherwise
                # continue testing against other rules
                if rule.stop:
                    break

        # set type
        return_val["classification"] = list(types)

        # run post-categorize hook
        return_val = self.post_categorize(return_val)

        return self.finalize(return_val)

    def finalize(self, return_val):
        """Before the types and attrs get passed to the
        importer they need to be altered by converting lists to
        sets, etc.
        """
        attrs = return_val
        return_val = {}

        # Get rid of defaultdict.
        for k, v in attrs.items():

            # Skip empties.
            if not isinstance(v, Iterable):
                continue

            if not isinstance(v, string_types):
                v = list(filter(None, v))

            # Get rid of sets.
            if isinstance(v, set):
                v = list(v)

            # Some vals should be strings, not seqs.
            if k == "actor" and len(v) == 1:
                v = v.pop()

            return_val[k] = v

        return return_val

    def pre_categorize(self, text):
        """A precategorization hook. Takes & returns text.  """
        return text

    def post_categorize(self, return_val):
        """A post-categorization hook. Takes & returns attrs dict.  """
        return return_val
