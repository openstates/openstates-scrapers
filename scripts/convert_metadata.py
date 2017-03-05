#!/usr/bin/env python

from __future__ import print_function

import csv
import sys
import json
import datetime
import importlib


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        return json.JSONEncoder.default(self, obj)


def get_districts(state):
    with open('manual_data/districts/{}.csv'.format(state)) as f:
        lower_max = 0
        upper_max = 0
        for d in csv.DictReader(f):
            if d['chamber'] == 'lower':
                if d['name'].isdigit():
                    if int(d['name']) > lower_max:
                        lower_max = int(d['name'])
                else:
                    lower_max = None
                    break
            if d['chamber'] == 'upper':
                if d['name'].isdigit():
                    if int(d['name']) > upper_max:
                        upper_max = int(d['name'])
                else:
                    upper_max = None
                    break

    return lower_max, upper_max


def convert(state):
    metadata = importlib.import_module('billy_metadata.' + state).metadata

    lower_max, upper_max = get_districts(state)

    tmpl = """import datetime
from pupa.scrape import Jurisdiction, Organization


class {classname}(Jurisdiction):
    division_id = "ocd-division/country:us/state:{abbr}"
    classification = "government"
    name = "{state}"
    url = "TODO"
    scrapers = {{
    }}
    parties = [
        {{'name': 'Republican'}},
        {{'name': 'Democratic'}}
    ]
    legislative_sessions = {sessions}
    ignored_scraped_sessions = [
{ignored}
    ]

    def get_organizations(self):
        legislature_name = "{legislature_name}"
        lower_chamber_name = "{lower_chamber_name}"
        lower_seats = {lower_seats}
        lower_title = "{lower_title}"
        upper_chamber_name = "{upper_chamber_name}"
        upper_seats = {upper_seats}
        upper_title = "{upper_title}"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            lower.add_post(
                label=str(n), role=upper_title,
                division_id='{{}}/sldu:{{}}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            upper.add_post(
                label=str(n), role=lower_title,
                division_id='{{}}/sldl:{{}}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower"""

    sessions = []
    for k, v in sorted(metadata['session_details'].items(), reverse=False):
        s = {'identifier': k,
             'name': v['display_name'],
             '_scraped_name': v['_scraped_name'],
             }
        if v.get('type'):
            s['classification'] = v['type']
        else:
            print(
                'Warning: Missing classification on session {}'.format(k),
                file=sys.stderr,
            )
        if v.get('start_date'):
            s['start_date'] = v.get('start_date')
        if v.get('end_date'):
            s['end_date'] = v.get('end_date')
        sessions.append(s)

    sessions = json.dumps(sessions, sort_keys=True, indent=4,
                          cls=DatetimeEncoder, separators=(',', ': '))
    sessions = sessions.replace('null', 'None')

    ignored = '        ' + '\n        '.join(
        repr(x) + ',' for x in metadata['_ignored_scraped_sessions']
    )

    data = {
        'abbr': metadata['abbreviation'],
        'state': metadata['name'],
        'classname': metadata['name'].replace(' ', ''),
        'sessions': sessions,
        'ignored': ignored,
        'legislature_name': metadata['legislature_name'],
        'lower_chamber_name': metadata['chambers']['lower']['name'],
        'lower_title': metadata['chambers']['lower']['title'],
        'lower_seats': lower_max,
        'upper_chamber_name': metadata['chambers']['upper']['name'],
        'upper_title': metadata['chambers']['upper']['title'],
        'upper_seats': upper_max,
    }
    print(tmpl.format(**data))


if __name__ == '__main__':
    convert(sys.argv[1])
