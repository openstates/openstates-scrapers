#!/usr/bin/env python
import datetime as dt
from cStringIO import StringIO
from lxml import etree

from sqlalchemy.sql import and_
from sqlalchemy import (Table, Column, Integer, String, ForeignKey,
                        DateTime, Text, Numeric, desc, create_engine,
                        UnicodeText)
from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy.ext.declarative import declarative_base

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

# Code for handling California's legislative info SQL dumps
# You can grab them from http://www.leginfo.ca.gov/FTProtocol.html
# Requires SQLAlchemy (tested w/ 0.5.3) and lxml

Base = declarative_base()

class Bill(Base):
    __tablename__ = "bill_tbl"
    
    bill_id = Column(String(19), primary_key=True)
    session_year = Column(String(8))
    session_num = Column(String(2))
    measure_type = Column(String(4))
    measure_num = Column(Integer)
    measure_state = Column(String(40))
    chapter_year = Column(String(4))
    chapter_type = Column(String(10))
    chapter_session_num = Column(String(2))
    chapter_num = Column(String(10))
    latest_bill_version_id = Column(String(30))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)
    current_location = Column(String(200))
    current_secondary_loc = Column(String(60))
    current_house = Column(String(60))
    current_status = Column(String(60))

    @property
    def short_bill_id(self):
        return "%s%d" % (self.measure_type, self.measure_num)
    
class BillVersion(Base):
    __tablename__ = "bill_version_tbl"

    bill_version_id = Column(String(30), primary_key=True)
    bill_id = Column(String(19), ForeignKey(Bill.bill_id))
    version_num = Column(Integer)
    bill_version_action_date = Column(DateTime)
    bill_version_action = Column(String(100))
    request_num = Column(String(10))
    subject = Column(String(1000))
    vote_required = Column(String(100))
    appropriation = Column(String(3))
    fiscal_committee = Column(String(3))
    local_program = Column(String(3))
    substantive_changes = Column(String(3))
    urgency = Column(String(3))
    taxlevy = Column(String(3))
    bill_xml = Column(UnicodeText)
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)

    bill = relation(Bill, backref=
                    backref('versions',
                            order_by=desc(bill_version_action_date)))

    @property
    def xml(self):
        if not '_xml' in self.__dict__:
            self._xml = etree.parse(StringIO(self.bill_xml.encode('utf-8')))
        return self._xml

    @property
    def title(self):
        texts = self.xml.xpath("//*[local-name() = 'Title']//text()")
        title = ''.join(texts).strip().encode('ascii', 'replace')
        return title

class BillVersionAuthor(Base):
    __tablename__ = "bill_version_authors_tbl"

    # Note: the primary_keys here are a lie - the actual table has no pk
    # but SQLAlchemy seems to demand one. Furthermore, I get strange
    # exceptions when trying to use bill_version_id as part of a
    # composite primary key.

    bill_version_id = Column(String(30),
                             ForeignKey(BillVersion.bill_version_id))
    type = Column(String(15))
    house = Column(String(100))
    name = Column(String(100), primary_key=True)
    contribution = Column(String(100))
    committee_members = Column(String(2000))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime, primary_key=True)
    primary_author_flg = Column(String(1))

    version = relation(BillVersion, backref=backref('authors'))

class BillAction(Base):
    __tablename__ = "bill_history_tbl"

    bill_id = Column(String(20), ForeignKey(Bill.bill_id))
    bill_history_id = Column(Numeric, primary_key=True)
    action_date = Column(DateTime)
    action = Column(String(2000))
    trans_uid = Column(String(20))
    trans_update_dt = Column(DateTime)
    action_sequence = Column(Integer)
    action_code = Column(String(5))
    action_status = Column(String(60))
    primary_location = Column(String(60))
    secondary_location = Column(String(60))
    ternary_location = Column(String(60))
    end_status = Column(String(60))

    bill = relation(Bill, backref=backref('actions'))

    @property
    def actor(self):
        # TODO: replace committee codes w/ names

        if not self.primary_location:
            return None

        actor = self.primary_location

        if self.secondary_location:
            actor += " (%s" % self.secondary_location

            if self.ternary_location:
                actor += " %s" % self.ternary_location

            actor += ")"

        return actor

class Legislator(Base):
    __tablename__ = 'legislator_tbl'

    district = Column(String(5), primary_key=True)
    session_year = Column(String(8), primary_key=True)
    legislator_name = Column(String(30), primary_key=True)
    house_type = Column(String(1), primary_key=True)
    author_name = Column(String(200))
    first_name = Column(String(30))
    last_name = Column(String(30))
    middle_initial = Column(String(1))
    name_suffix = Column(String(12))
    name_title = Column(String(34))
    web_name_title = Column(String(34))
    party = Column(String(4))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)

class Motion(Base):
    __tablename__ = "bill_motion_tbl"

    motion_id = Column(Integer, primary_key=True)
    motion_text = Column(String(250))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)

class Location(Base):
    __tablename__ = "location_code_tbl"

    session_year = Column(String(8), primary_key=True)
    location_code = Column(String(6), primary_key=True)
    location_type = Column(String(1))
    consent_calendar_code = Column(String(2))
    description = Column(String(60))
    long_description = Column(String(200))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)

class VoteSummary(Base):
    __tablename__ = "bill_summary_vote_tbl"

    bill_id = Column(String(20), ForeignKey(Bill.bill_id))
    location_code = Column(String(6), ForeignKey(Location.location_code))
    vote_date_time = Column(DateTime, primary_key=True)
    vote_date_seq = Column(Integer, primary_key=True)
    motion_id = Column(Integer, ForeignKey(Motion.motion_id))
    ayes = Column(Integer)
    noes = Column(Integer)
    abstain = Column(Integer)
    vote_result = Column(String(6))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)

    bill = relation(Bill, backref=backref('votes'))
    motion = relation(Motion)
    location = relation(Location)

    @property
    def threshold(self):
        # This may not always be true...
        if self.location_code != "AFLOOR" and self.location_code != "SFLOOR":
            return '1/2'

        # Get the associated bill version (probably?)
        version = filter(lambda v:
                            v.bill_version_action_date <= self.vote_date_time,
                        self.bill.versions)[0]

        if version.vote_required == 'Majority':
            return '1/2'
        else:
            return '2/3'

class VoteDetail(Base):
    __tablename__ = "bill_detail_vote_tbl"

    bill_id = Column(String(20), ForeignKey(Bill.bill_id),
                     ForeignKey(VoteSummary.bill_id))
    location_code = Column(String(6), ForeignKey(VoteSummary.location_code))
    legislator_name = Column(String(50), primary_key=True)
    vote_date_time = Column(DateTime, ForeignKey(VoteSummary.vote_date_time))
    vote_date_seq = Column(Integer, ForeignKey(VoteSummary.vote_date_seq))
    vote_code = Column(String(5), primary_key=True)
    motion_id = Column(Integer, ForeignKey(VoteSummary.motion_id))
    trans_uid = Column(String(30), primary_key=True)
    trans_update = Column(DateTime, primary_key=True)

    bill = relation(Bill, backref=backref('detail_votes'))
    summary = relation(VoteSummary, primaryjoin=
                       and_(VoteSummary.bill_id == bill_id,
                            VoteSummary.location_code == location_code,
                            VoteSummary.vote_date_time == vote_date_time,
                            VoteSummary.vote_date_seq == vote_date_seq,
                            VoteSummary.motion_id == motion_id),
                       backref=backref('votes'))

class CASQLImporter(LegislationScraper):
    state = 'ca'

    def __init__(self, host, user, pw, db='capublic'):
        self.engine = create_engine('mysql://%s:%s@%s/%s?charset=utf8' % (
                user, pw, host, db))
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def scrape_bills(self, chamber, year):
        if int(year) < 1989 or int(year) > dt.datetime.today().year:
            raise NoDataForYear(year)

        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        if chamber == 'upper':
            measure_abbr = 'SB'
            chamber_name = 'SENATE'
            house_type = 'S'
        else:
            measure_abbr = 'AB'
            chamber_name = 'ASSEMBLY'
            house_type = 'A'
        
        year2 = str(int(year) + 1)
        session = "%s%s" % (year, year2)

        legislators = self.session.query(Legislator).filter_by(
            session_year=session).filter_by(
            house_type=house_type)

        for legislator in legislators:
            self.add_legislator(chamber, session, legislator.district,
                                legislator.legislator_name,
                                legislator.first_name,
                                legislator.last_name, legislator.middle_initial,
                                legislator.name_suffix, legislator.party)

        bills = self.session.query(Bill).filter_by(
            session_year=session).filter_by(
            measure_type=measure_abbr)

        for bill in bills:
            bill_session = "%s%s" % (session, bill.session_num)
            bill_id = bill.short_bill_id
            version = bill.versions[0]
            self.add_bill(chamber, bill_session, bill_id, version.title)

            for author in version.authors:
                if author.house == chamber_name:
                    self.add_sponsorship(chamber, bill_session, bill_id,
                                         author.contribution,
                                         author.name)

            for action in bill.actions:
                if not action.action:
                    # NULL action text seems to be an error on CA's part,
                    # unless it has some meaning I'm missing
                    continue
                actor = action.actor or chamber
                self.add_action(chamber, bill_session, bill_id, actor,
                                action.action, action.action_date)

            for vote in bill.votes:
                if vote.vote_result == '(PASS)':
                    result = True
                else:
                    result = False
                yes = []
                no = []
                other = []
                for record in vote.votes:
                    if record.vote_code == 'AYE':
                        yes.append(record.legislator_name)
                    elif record.vote_code.startswith('NO'):
                        no.append(record.legislator_name)
                    else:
                        other.append(record.legislator_name)
                self.add_vote(chamber, bill_session, bill_id,
                              vote.vote_date_time,
                              vote.location.description,
                              vote.motion.motion_text,
                              result, vote.ayes, vote.noes, vote.abstain,
                              yes, no, other, vote.threshold)

if __name__ == '__main__':
    CASQLImporter('localhost', 'USER', 'PASSWORD').run()
