import os
import re
from collections import defaultdict

from billy.core import settings
from billy.scrape.events import EventScraper, Event
from .models import CACommitteeHearing, CALocation

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import pytz


class CAEventScraper(EventScraper):
    jurisdiction = 'ca'

    _tz = pytz.timezone('US/Pacific')

    def __init__(self, metadata, host='127.0.0.1', user='', pw='',
                 db='capublic', **kwargs):
        super(CAEventScraper, self).__init__(metadata, **kwargs)

        if not user:
            user = os.environ.get('MYSQL_USER',
                                  getattr(settings, 'MYSQL_USER', 'root'))
        if not pw:
            pw = os.environ.get('MYSQL_PASSWORD',
                                getattr(settings, 'MYSQL_PASSWORD', ''))

        if user and pw:
            conn_str = 'mysql://%s:%s@' % (user, pw)
        else:
            conn_str = 'mysql://'
        conn_str = '%s%s/%s?charset=utf8' % (
            conn_str, host, db)
        self.engine = create_engine(conn_str)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def scrape(self, chamber, session):
        grouped_hearings = defaultdict(list)

        for hearing in self.session.query(CACommitteeHearing):
            location = self.session.query(CALocation).filter_by(
                location_code=hearing.location_code)[0].description

            date = self._tz.localize(hearing.hearing_date)

            chamber_abbr = location[0:3]
            event_chamber = {'Asm': 'lower', 'Sen': 'upper'}[chamber_abbr]

            if event_chamber != chamber:
                continue

            grouped_hearings[(location, date)].append(hearing)

        for ((location, date), hearings) in grouped_hearings.iteritems():

            # Get list of bill_ids from the database.
            bill_ids = [hearing.bill_id for hearing in hearings]
            bills = ["%s %s" % re.match(r'\d+([^\d]+)(\d+)', bill).groups()
                     for bill in bill_ids]

            # Dereference the committee_nr number and get display name.
            msg = 'More than one committee meeting at (location, date) %r'
            msg = msg % ((location, date),)
            assert len(set(hearing.committee_nr for hearing in hearings)) == 1, msg
            committee_name = _committee_nr[hearings.pop().committee_nr]

            desc = 'Committee Meeting: ' + committee_name
            event = Event(session, date, 'committee:meeting', desc,
                          location=committee_name)
            for bill_id in bills:
                if 'B' in bill_id:
                    type_ = 'bill'
                else:
                    type_ = 'resolution'
                event.add_related_bill(bill_id, type=type_,
                                       description='consideration')

            event.add_participant('host', committee_name + ' Committee',
                                  'committee', chamber=chamber)
            event.add_source('ftp://www.leginfo.ca.gov/pub/bill/')

            self.save_event(event)

# A mapping of committee_nr numbers to committee names they
# (probably) represent, based on direct correlation they bore
# to hearing locations that resemble committee names in
# the location_code_tbl in the db dump.
_committee_nr = {
    1L: u'Assembly Agriculture',
    2L: u'Assembly Accountability and Administrative Review',
    3L: u'Assembly Education',
    4L: u'Assembly Elections and Redistricting',
    5L: u'Assembly Environmental Safety and Toxic Materials',
    6L: u'Assembly Budget X1',
    7L: u'Assembly Governmental Organization',
    8L: u'Assembly Health',
    9L: u'Assembly Higher Education',
    10L: u'Assembly Housing and Community Development',
    11L: u'Assembly Human Services',
    13L: u'Assembly Judiciary',
    14L: u'Assembly Labor and Employment',
    15L: u'Assembly Local Government',
    16L: u'Assembly Natural Resources',
    17L: u'Assembly Public Employees, Retirement/Soc Sec',
    18L: u'Assembly Public Safety',
    19L: u'Assembly Revenue and Taxation',
    20L: u'Assembly Rules',
    22L: u'Assembly Transportation',
    23L: u'Assembly Utilities and Commerce',
    24L: u'Assembly Water, Parks and Wildlife',
    25L: u'Assembly Appropriations',
    27L: u'Assembly Banking and Finance',
    28L: u'Assembly Insurance',
    29L: u'Assembly Budget',
    30L: u'Assembly Public Health and Developmental Services',
    31L: u'Assembly Aging and Long Term Care',
    32L: u'Assembly Privacy and Consumer Protection',
    33L: u'Assembly Business, Professions and Consumer Protection ',
    34L: u'Assembly Jobs, Economic Development, and the Economy',
    35L: u'Assembly Finance',
    37L: u'Assembly Arts, Entertainment, Sports, Tourism, and Internet Media',
    38L: u'Assembly Veterans Affairs',
    40L: u'Senate Agriculture',
    42L: u'Senate Business, Professions and Economic Development',
    44L: u'Senate Education',
    45L: u'Senate Elections and Constitutional Amendments',
    48L: u'Senate Governmental Organization',
    51L: u'Senate Labor and Industrial Relations',
    53L: u'Senate Judiciary',
    55L: u'Senate Natural Resources and Water',
    56L: u'Senate Public Employment and Retirement',
    58L: u'Senate Rules',
    59L: u'Senate Transportation and Housing',
    60L: u'Senate Health',
    61L: u'Senate Appropriations',
    62L: u'Senate Budget and Fiscal Review',
    64L: u'Senate Environmental Quality',
    66L: u'Senate Veterans Affairs',
    67L: u'Senate Transportation and Infrastructure Development',
    68L: u'Senate Public Health and Developmental Services',
    69L: u'Senate Banking and Financial Institutions',
    70L: u'Senate Insurance',
    71L: u'Senate Energy, Utilities and Communications',
    72L: u'Senate Public Safety',
    73L: u'Senate Governance and Finance',
    74L: u'Senate Human Services'
 }
