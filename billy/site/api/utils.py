import os
import csv

from billy.utils import metadata

_census_to_district = None
_district_to_census = None


def _load_census_mapping():
    global _census_to_district
    global _district_to_census
    _census_to_district = {}
    _district_to_census = {}

    path = os.path.join(os.path.dirname(__file__),
                        "../../../manual_data/districts.csv")
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            _census_to_district[tuple(row[0:3])] = row[3].strip()
            _district_to_census[(row[0], row[1], row[3])] = row[2].strip()


def district_from_census_name(state, chamber, census_name):
    """
    In some states the Census Bureau names districts differently than
    our primary sources. This uses a CSV file located at
    manual_data/districts.csv to fix troublemakers.
    """
    if not _district_to_census:
        _load_census_mapping()

    try:
        return _census_to_district[(state, chamber, census_name)]
    except KeyError:
        return census_name.split('District ')[1]


def district_slug(state, chamber, district):
    if not _district_to_census:
        _load_census_mapping()

    try:
        census_name = _district_to_census[(state, chamber, district)]
    except KeyError:
        if chamber == 'upper':
            census_name = 'State Senate District %s' % district
        else:
            if state == 'md':
                if district[-1].isalpha():
                    census_name = 'State Legislative Subdistrict ' + district
                else:
                    census_name = 'State Legislative District ' + district

            meta = metadata(state)
            lower_name = meta['lower_chamber_name']
            if lower_name.startswith('House'):
                census_name = "State House District %s" % district
            else:
                census_name = "Assembly District %s" % district

    if chamber == 'lower':
        prefix = 'sldl'
    else:
        prefix = 'sldu'

    return "%s-%s-%s" % (prefix, state.lower(),
                         census_name.replace(' ', '-').lower())
