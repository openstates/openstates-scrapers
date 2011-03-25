import os
import csv

_census_mapping = None


def _load_census_mapping():
    global _census_mapping
    _census_mapping = {}
    path = os.path.join(os.path.dirname(__file__),
                        "../../../manual_data/districts.csv")
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            _census_mapping[tuple(row[0:3])] = row[3].strip()


def district_from_census_name(state, chamber, census_name):
    """
    In some states the Census Bureau names districts differently than
    our primary sources. This uses a CSV file located at
    manual_data/districts.csv to fix troublemakers.
    """
    if not _census_mapping:
        _load_census_mapping()

    try:
        return _census_mapping[(state, chamber, census_name)]
    except KeyError:
        return census_name.split('District ')[1]
