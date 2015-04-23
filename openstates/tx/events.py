from openstates.utils import LXMLMixin
import re
import datetime as dt

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class TXEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'tx'
    _tz = pytz.timezone('US/Central')

    def scrape(self, chamber, session):
        if not session.startswith(session):  # XXX: Fixme
            raise NoDataForPeriod(session)

        self.scrape_committee_upcoming(session, chamber)

    def scrape_event_page(self, session, chamber, url, datetime):
        page = self.lxmlize(url)
        info = page.xpath("//p")
        metainf = {}
        plaintext = ""
        for p in info:
            content = re.sub("\s+", " ", p.text_content())
            plaintext += content + "\n"
            if ":" in content:
                key, val = content.split(":", 1)
                metainf[key.strip()] = val.strip()
        ctty = metainf['COMMITTEE']
        where = metainf['PLACE']
        if "CHAIR" in where:
            where, chair = where.split("CHAIR:")
            metainf['PLACE'] = where.strip()
            metainf['CHAIR'] = chair.strip()

        chair = None
        if "CHAIR" in metainf:
            chair = metainf['CHAIR']

        plaintext = re.sub("\s+", " ", plaintext).strip()
        regexp = r"(S|J|H)(B|M|R) (\d+)"
        bills = re.findall(regexp, plaintext)

        event = Event(session,
                      datetime,
                      'committee:meeting',
                      ctty,
                      chamber=chamber,
                      location=where,
                      agenda=plaintext)
        event.add_source(url)
        event.add_participant('host', ctty, 'committee', chamber=chamber)
        if not chair is None:
            event.add_participant('chair', chair, 'legislator', chamber=chamber)

        for bill in bills:
            chamber, type, number = bill
            bill_id = "%s%s %s" % ( chamber, type, number )
            event.add_related_bill(bill_id,
                                   type='consideration',
                                   description='Bill up for discussion')

        self.save_event(event)

    def scrape_page(self, session, chamber, url):
        try:
            page = self.lxmlize(url)
            events = page.xpath("//a[contains(@href, 'schedules/html')]")
            for event in events:
                peers = event.getparent().getparent().xpath("./*")
                date = peers[0].text_content()
                time = peers[1].text_content()
                tad = "%s %s" % ( date, time )
                tad = re.sub(r"(PM|AM).*", r"\1", tad)
                tad_fmt = "%m/%d/%Y %I:%M %p"
                if "AM" not in tad and "PM" not in tad:
                    tad_fmt = "%m/%d/%Y"
                    tad = date

                # Time expressed as 9:00 AM, Thursday, May 17, 2012
                datetime = dt.datetime.strptime(tad, tad_fmt)
                self.scrape_event_page(session, chamber, event.attrib['href'],
                                      datetime)
        except lxml.etree.XMLSyntaxError:
            pass  # lxml.etree.XMLSyntaxError: line 248: htmlParseEntityRef: expecting ';'
            # XXX: Please fix this, future hacker. I think this might be a problem
            # with lxml -- due diligence on this is needed.
            #                                              -- PRT

    def scrape_upcoming_page(self, session, chamber, url):
        page = self.lxmlize(url)
        date = None
        thyme = None

        for row in page.xpath(".//tr"):
            title = row.xpath(".//div[@class='sectionTitle']")
            if len(title) > 0:
                date = title[0].text_content()
                #print "Found date ", date
            time = row.xpath(".//td/strong")
            if len(time) > 0:
                thyme = time[0].text_content()
                #print "Found time ", thyme

            events = row.xpath(".//a[contains(@href, 'schedules/html')]")
            for event in events:
                datetime = "%s %s" % ( date, thyme )
                replace = {
                    r"of .*": "",
                    "or recess": "",
                    "see below": "",
                    "See Below": "",
                    "See below": "",
                    "of the House": "",
                    "of the Senate": "",
                    r"on Article .*": "",
                    "Finance Committee": "",
                    "or upon adjournment": "",
                    "9:00 AM Mountain Time": "",
                    "or upon the adjournment": "",
                    "of the House and the Senate": "",
                    r"or upon final adjourn./recess": "",
                    "or 30 minutes upon adjournment": "",
                    r"30 minutes upon adjourn\.": "",
                    "or the Senate Finance Committee": "",
                    "During reading and referral of bills": "",
                    "and House Chambers, whichever is later.": "",
                    "or during reading and referral of bills": "",
                    r"(or 15 minutes after adjournment of the .*)": "",
                    r"Upon final adjourn./recess": "",
                    "or upon recess/adjournment": "",
                    "upon adjourn.": "",
                    "Upon Adjournment": "",
                    "Upon first adjournment": "",
                    "Upon lunch recess": "",
                }
                for rep in replace:
                    datetime = re.sub(rep, replace[rep], datetime)

                datetime = datetime.strip()

                try:
                    datetime = dt.datetime.strptime(datetime, "%A, %B %d, %Y %I:%M %p")
                except ValueError:
                    datetime = dt.datetime.strptime(datetime, "%A, %B %d, %Y")

                self.scrape_event_page(session, chamber, event.attrib['href'],
                                      datetime)

    def scrape_committee_upcoming(self, session, chamber):
        chid = {'upper': 'S',
                        'lower': 'H',
                        'other': 'J'}[chamber]

        url = "http://www.capitol.state.tx.us/Committees/Committees.aspx" + \
                "?Chamber=" + chid

        page = self.lxmlize(url)
        refs = page.xpath("//div[@id='content']//a")
        for ref in refs:
            self.scrape_page(session, chamber, ref.attrib['href'])


        url = "http://www.capitol.state.tx.us/Committees/MeetingsUpcoming.aspx" + \
                "?Chamber=" + chid
        self.scrape_upcoming_page(session, chamber, url)
