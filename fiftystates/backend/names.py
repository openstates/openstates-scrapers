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

    def __init__(self):
        self.names = {}

    def __setitem__(self, name, obj):
        """
        Expects a dictionary with full_name, first_name, last_name and
        middle_name elements as key.

        While this can grow quickly, we should never be dealing with
        more than a few hundred legislators at a time so don't worry about
        it.
        """
        # We throw possible forms of this name into a set because we
        # don't want to try to add the same form twice for the same
        # name
        forms = set()
        forms.add(name['full_name'].replace('.', ''))
        forms.add(name['last_name'])


        if name['first_name']:
            forms.add("%s, %s" % (name['last_name'], name['first_name']))
            forms.add("%s %s" % (name['first_name'], name['last_name']))
            forms.add("%s, %s" % (name['last_name'], name['first_name'][0]))
            forms.add("%s (%s)" % (name['last_name'], name['first_name']))
            forms.add("%s %s" % (name['first_name'][0], name['last_name']))
            forms.add("%s (%s)" % (name['last_name'], name['first_name'][0]))

            if name['middle_name']:
                forms.add("%s, %s %s" % (name['last_name'], name['first_name'],
                                         name['middle_name']))
                forms.add("%s, %s %s" % (name['last_name'],
                                         name['first_name'][0],
                                         name['middle_name']))
                forms.add("%s %s %s" % (name['first_name'],
                                        name['middle_name'],
                                        name['last_name']))
                forms.add("%s, %s %s" % (name['last_name'],
                                         name['first_name'][0],
                                         name['middle_name'][0]))
                forms.add("%s %s %s" % (name['first_name'],
                                        name['middle_name'][0],
                                        name['last_name']))
                forms.add("%s, %s %s" % (name['last_name'],
                                         name['first_name'],
                                         name['middle_name'][0]))
                forms.add("%s, %s.%s." % (name['last_name'],
                                          name['first_name'][0],
                                          name['middle_name'][0]))


        for form in forms:
            form = form.replace('.', '').lower()
            if form in self.names:
                self.names[form] = None
            else:
                self.names[form] = obj

    def __getitem__(self, name):
        """
        If this matcher has uniquely seen a matching name, return its
        value. Otherwise, return None.
        """
        name = name.strip().replace('.', '').lower()
        if name in self.names:
            return self.names[name]
        return None
