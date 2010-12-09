from fiftystates.backend import db

__matchers = {}


def get_legislator_id(state, session, chamber, name):
    try:
        matcher = __matchers[(state, session, chamber)]
    except KeyError:
        matcher = init_name_matcher(state, session, chamber)
        __matchers[(state, session, chamber)] = matcher

    return matcher[name]


def init_name_matcher(state, session, chamber):
    matcher = NameMatcher()

    elemMatch = {'state': state, 'type': 'member'}

    metadata = db.metadata.find_one({'_id': state})
    for term in metadata['terms']:
        if session in term['sessions']:
            elemMatch['term'] = term['name']
            break
    else:
        raise Exception("bad session: " + session)

    if chamber and chamber != 'both':
        elemMatch['chamber'] = chamber

    for legislator in db.legislators.find({
            'roles': {'$elemMatch': elemMatch}}):
        if 'middle_name' not in legislator:
            legislator['middle_name'] = ''

        matcher[legislator] = legislator['_id']

    return matcher


class NameMatcher(object):
    """
    Match various forms of a name, provided they uniquely identify
    a person from everyone else we've seen.

    Given the name object:
     {'full_name': 'Michael J. Stephens', 'first_name': 'Michael',
      'last_name': 'Stephens', 'middle_name': 'Joseph'}
    we will match these forms:
     Michael J. Stephens
     Michael Stephens
     Stephens
     Stephens, Michael
     Stephens, M
     Stephens, Michael Joseph
     Stephens, Michael J
     Stephens, M J
     M Stephens
     M J Stephens
     Michael Joseph Stephens
     Stephens (M)

    Tests:

    >>> nm = NameMatcher()
    >>> nm[{'full_name': 'Michael J. Stephens', 'first_name': 'Michael', \
            'last_name': 'Stephens', 'middle_name': 'J'}] = 1
    >>> assert nm['Michael J. Stephens'] == 1
    >>> assert nm['Stephens'] == 1
    >>> assert nm['Michael Stephens'] == 1
    >>> assert nm['Stephens, M'] == 1
    >>> assert nm['Stephens, Michael'] == 1
    >>> assert nm['Stephens, M J'] == 1

    Add a similar name:

    >>> nm[{'full_name': 'Mike J. Stephens', 'first_name': 'Mike', \
            'last_name': 'Stephens', 'middle_name': 'Joseph'}] = 2

    Unique:

    >>> assert nm['Mike J. Stephens'] == 2
    >>> assert nm['Mike Stephens'] == 2
    >>> assert nm['Michael Stephens'] == 1

    Not unique anymore:

    >>> assert nm['Stephens'] == None
    >>> assert nm['Stephens, M'] == None
    >>> assert nm['Stephens, M J'] == None
    """

    def _normalize(self, name):
        return name.strip().lower().replace('.', '')

    def __init__(self):
        self._names = {}
        self._codes = {}

    def __setitem__(self, name, obj):
        """
        Expects a dictionary with full_name, first_name, last_name and
        middle_name elements as key.

        While this can grow quickly, we should never be dealing with
        more than a few hundred legislators at a time so don't worry about
        it.
        """
        if '_code' in name:
            code = name['_code']
            if code in self._codes:
                raise ValueError("non-unique legislator code: %s" % code)
            self._codes[code] = obj

        # We throw possible forms of this name into a set because we
        # don't want to try to add the same form twice for the same
        # name
        forms = set()

        def add_form(form):
            forms.add(self._normalize(form))

        add_form(name['full_name'])
        add_form(name['_scraped_name'])
        add_form(name['last_name'])

        if name['first_name']:
            add_form("%s, %s" % (name['last_name'], name['first_name']))
            add_form("%s %s" % (name['first_name'], name['last_name']))
            add_form("%s, %s" % (name['last_name'], name['first_name'][0]))
            add_form("%s (%s)" % (name['last_name'], name['first_name']))
            add_form("%s %s" % (name['first_name'][0], name['last_name']))
            add_form("%s (%s)" % (name['last_name'], name['first_name'][0]))

            if name['middle_name']:
                add_form("%s, %s %s" % (name['last_name'], name['first_name'],
                                         name['middle_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                         name['first_name'][0],
                                         name['middle_name']))
                add_form("%s %s %s" % (name['first_name'],
                                        name['middle_name'],
                                        name['last_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                         name['first_name'][0],
                                         name['middle_name'][0]))
                add_form("%s %s %s" % (name['first_name'],
                                        name['middle_name'][0],
                                        name['last_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                         name['first_name'],
                                         name['middle_name'][0]))
                add_form("%s, %s.%s." % (name['last_name'],
                                          name['first_name'][0],
                                          name['middle_name'][0]))

        for form in forms:
            form = self._normalize(form)
            if form in self._names:
                self._names[form] = None
            else:
                self._names[form] = obj


    def __getitem__(self, name):
        """
        If this matcher has uniquely seen a matching name, return its
        value. Otherwise, return None.
        """
        if name in self._codes:
            return self._codes[name]

        name = self._normalize(name)
        if name in self._names:
            return self._names[name]
        return None
