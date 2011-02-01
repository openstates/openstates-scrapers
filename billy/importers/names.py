import re
import csv
import os.path

from billy import db

__matchers = {}


def get_legislator_id(state, session, chamber, name):
    try:
        matcher = __matchers[(state, session, chamber)]
    except KeyError:
        matcher = init_name_matcher(state, session, chamber)
        __matchers[(state, session, chamber)] = matcher

    return matcher.match(name)


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

    if chamber and chamber not in ('both', 'joint'):
        elemMatch['chamber'] = chamber

    for legislator in db.legislators.find({
            'roles': {'$elemMatch': elemMatch}}):
        if 'middle_name' not in legislator:
            legislator['middle_name'] = ''

        matcher.learn(legislator)

    manual_path = os.path.join(os.path.dirname(__file__),
                               "../../manual_data/leg_ids/%s.csv" % state)
    matcher.learn_manual_matches(manual_path)

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
            'last_name': 'Stephens', 'middle_name': 'J', \
            '_scraped_name': 'Michael J. Stephens'}] = 1
    >>> assert nm['Michael J. Stephens'] == 1
    >>> assert nm['Stephens'] == 1
    >>> assert nm['Michael Stephens'] == 1
    >>> assert nm['Stephens, M'] == 1
    >>> assert nm['Stephens, Michael'] == 1
    >>> assert nm['Stephens, M J'] == 1

    Add a similar name:

    >>> nm[{'full_name': 'Mike J. Stephens', 'first_name': 'Mike', \
            'last_name': 'Stephens', 'middle_name': 'Joseph', \
            '_scraped_name': 'Mike J. Stephens'}] = 2

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
        name = re.sub(r'^(Senator|Representative) ', '', name)
        return name.strip().lower().replace('.', '')

    def __init__(self):
        self._names = {}
        self._codes = {}
        self._manual = {}

    def learn_manual_matches(self, path):
        try:
            with open(path) as f:
                reader = csv.reader(f)

                for (term, name, leg_id) in reader:
                    self._manual[name] = leg_id
        except IOError:
            pass

    def learn(self, legislator):
        """
        Expects a dictionary with full_name, first_name, last_name and
        middle_name elements as key.

        While this can grow quickly, we should never be dealing with
        more than a few hundred legislators at a time so don't worry about
        it.
        """
        name, obj = legislator, legislator['_id']

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


    def match(self, name):
        """
        If this matcher has uniquely seen a matching name, return its
        value. Otherwise, return None.
        """
        try:
            return self._manual[name]
        except KeyError:
            pass

        try:
            return self._codes[name]
        except KeyError:
            pass

        name = self._normalize(name)
        return self._names.get(name, None)
