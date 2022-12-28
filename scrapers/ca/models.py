from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Numeric,
    UnicodeText,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import and_
from sqlalchemy.orm import backref, relation, foreign
from sqlalchemy.ext.declarative import declarative_base

from lxml import etree

Base = declarative_base()


class CABill(Base):
    __tablename__ = "bill_tbl"

    bill_id = Column(String(20), primary_key=True)
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

    actions = relation(
        "CABillAction", backref=backref("bill"), order_by="CABillAction.bill_history_id"
    )

    versions = relation(
        "CABillVersion",
        backref=backref("bill"),
        order_by="desc(CABillVersion.version_num)",
    )

    votes = relation(
        "CAVoteSummary",
        backref=backref("bill"),
        order_by="CAVoteSummary.vote_date_time",
    )

    analyses = relation(
        "CABillAnalysis",
        backref=backref("bill"),
        order_by="CABillAnalysis.analysis_date",
    )

    @property
    def short_bill_id(self):
        return "%s%d" % (self.measure_type, self.measure_num)


class CABillVersion(Base):
    __tablename__ = "bill_version_tbl"

    bill_version_id = Column(String(30), primary_key=True)
    bill_id = Column(String(19), ForeignKey(CABill.bill_id))
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

    @property
    def xml(self):
        if "_xml" not in self.__dict__:
            self._xml = etree.fromstring(
                self.bill_xml.encode("utf-8"), etree.XMLParser(recover=True)
            )
        return self._xml

    @property
    def title(self):
        text = self.xml.xpath("string(//*[local-name() = 'Title'])") or ""
        return text.strip()

    @property
    def short_title(self):
        text = self.xml.xpath("string(//*[local-name() = 'Subject'])") or ""
        return text.strip()


class CABillVersionAuthor(Base):
    __tablename__ = "bill_version_authors_tbl"

    # Note: the primary_keys here are a lie - the actual table has no pk
    # but SQLAlchemy seems to demand one. Furthermore, I get strange
    # exceptions when trying to use bill_version_id as part of a
    # composite primary key.

    bill_version_id = Column(String(30), ForeignKey(CABillVersion.bill_version_id))
    type = Column(String(15))
    house = Column(String(100))
    name = Column(String(100), primary_key=True)
    contribution = Column(String(100))
    committee_members = Column(String(2000))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime, primary_key=True)
    primary_author_flg = Column(String(1))

    version = relation(CABillVersion, backref=backref("authors"))


class CABillAnalysis(Base):
    __tablename__ = "bill_analysis_tbl"

    analysis_id = Column(Numeric, primary_key=True)
    bill_id = Column(String(20), ForeignKey(CABill.bill_id))
    house = Column(String(1))
    analysis_type = Column(String(100))
    committee_code = Column(String(6))
    committee_name = Column(String(200))
    amendment_author = Column(String(100))
    analysis_date = Column(DateTime)
    amendment_date = Column(DateTime)
    page_num = Column(Numeric)
    source_doc = Column(mysql.LONGBLOB)
    released_floor = Column(String(1))
    active_flg = Column(String(1), default="Y")
    trans_uid = Column(String(20))
    trans_update = Column(DateTime)


class CABillAction(Base):
    __tablename__ = "bill_history_tbl"

    bill_id = Column(String(20), ForeignKey(CABill.bill_id))
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


class CALegislator(Base):
    __tablename__ = "legislator_tbl"

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


class CAMotion(Base):
    __tablename__ = "bill_motion_tbl"

    motion_id = Column(Integer, primary_key=True)
    motion_text = Column(String(250))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)


class CALocation(Base):
    __tablename__ = "location_code_tbl"

    session_year = Column(String(8), primary_key=True)
    location_code = Column(String(6), primary_key=True)
    location_type = Column(String(1), primary_key=True)
    consent_calendar_code = Column(String(2), primary_key=True)
    description = Column(String(60))
    long_description = Column(String(200))
    active_flg = Column(String(1))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime)


class CAVoteSummary(Base):
    __tablename__ = "bill_summary_vote_tbl"

    bill_id = Column(String(20), ForeignKey(CABill.bill_id), primary_key=True)
    location_code = Column(
        String(6), ForeignKey(CALocation.location_code), primary_key=True
    )
    vote_date_time = Column(DateTime, primary_key=True)
    vote_date_seq = Column(Integer, primary_key=True)
    motion_id = Column(Integer, ForeignKey(CAMotion.motion_id), primary_key=True)
    ayes = Column(Integer)
    noes = Column(Integer)
    abstain = Column(Integer)
    vote_result = Column(String(6))
    trans_uid = Column(String(30))
    trans_update = Column(DateTime, primary_key=True)

    motion = relation(CAMotion)
    location = relation(CALocation)

    @property
    def threshold(self):
        # This may not always be true...
        if self.location_code != "AFLOOR" and self.location_code != "SFLOOR":
            return "1/2"

        # Get the associated bill version (probably?)
        version = next(
            filter(
                lambda v: v.bill_version_action_date <= self.vote_date_time,
                self.bill.versions,
            )
        )

        if version.vote_required == "Majority":
            return "1/2"
        else:
            return "2/3"


class CAVoteDetail(Base):
    __tablename__ = "bill_detail_vote_tbl"

    bill_id = Column(String(20), ForeignKey(CABill.bill_id), primary_key=True)
    location_code = Column(
        String(6), ForeignKey(CAVoteSummary.location_code), primary_key=True
    )
    legislator_name = Column(String(50), primary_key=True)
    vote_date_time = Column(
        DateTime, ForeignKey(CAVoteSummary.vote_date_time), primary_key=True
    )
    vote_date_seq = Column(
        Integer, ForeignKey(CAVoteSummary.vote_date_seq), primary_key=True
    )
    vote_code = Column(String(5), primary_key=True)
    motion_id = Column(Integer, ForeignKey(CAVoteSummary.motion_id), primary_key=True)
    trans_uid = Column(String(30), primary_key=True)
    trans_update = Column(DateTime, primary_key=True)

    bill = relation(
        CABill,
        primaryjoin="CABill.bill_id == foreign(CAVoteDetail.bill_id)",
        backref=backref("detail_votes"),
    )
    summary = relation(
        CAVoteSummary,
        primaryjoin=and_(
            CAVoteSummary.bill_id == foreign(bill_id),
            CAVoteSummary.location_code == location_code,
            CAVoteSummary.vote_date_time == vote_date_time,
            CAVoteSummary.vote_date_seq == vote_date_seq,
            CAVoteSummary.motion_id == motion_id,
        ),
        backref=backref("votes"),
        overlaps="bill,detail_votes",
    )


class CACommitteeHearing(Base):
    __tablename__ = "committee_hearing_tbl"

    bill_id = Column(
        String(20),
        ForeignKey(CABill.bill_id),
        ForeignKey(CAVoteSummary.bill_id),
        primary_key=True,
    )
    committee_type = Column(String(2), primary_key=True)
    committee_nr = Column(Integer, primary_key=True)
    hearing_date = Column(DateTime, primary_key=True)
    location_code = Column(String(6), primary_key=True)
    trans_uid = Column(String(30), primary_key=True)
    trans_update_date = Column(DateTime, primary_key=True)

    bill = relation(CABill, backref=backref("committee_hearings"))
