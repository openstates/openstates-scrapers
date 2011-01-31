import os
import re
import datetime
from collections import defaultdict

from billy.conf import settings
from billy.scrape.events import EventScraper, Event
from openstates.ca import metadata
from openstates.ca.models import CACommitteeHearing, CALocation

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine

import pytz


class CAEventScraper(EventScraper):
    state = 'ca'

    _tz = pytz.timezone('US/Pacific')

    def __init__(self, metadata, host='127.0.0.1', user='', pw='',
                 db='capublic', **kwargs):
        super(CAEventScraper, self).__init__(metadata, **kwargs)

        if not user:
            user = os.environ.get('MYSQL_USER',
                                  getattr(settings, 'MYSQL_USER', ''))
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
        bills_discussed = defaultdict(list)

        for hearing in self.session.query(CACommitteeHearing):
            location = self.session.query(CALocation).filter_by(
                location_code=hearing.location_code)[0].description

            date = self._tz.localize(hearing.hearing_date)

            chamber_abbr = location[0:3]
            event_chamber = {'Asm': 'lower', 'Sen': 'upper'}[chamber_abbr]

            if event_chamber != chamber:
                continue

            bills_discussed[(location, date)].append(hearing.bill_id)

        for ((location, date), bills) in bills_discussed.iteritems():
            desc = 'Committee Meeting\n%s\nDiscussed: %s' % (location,
                                                             ', '.join(bills))

            event = Event(session, date, 'committee:meeting', desc,
                          location=location)
            event.add_participant('committee', location)

            self.save_event(event)
