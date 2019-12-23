import datetime
import re
from pytz import timezone as tmz

from lxml import html

from pupa.scrape import Event, Scraper

# from . import session_metadata


class AZEventScraper(Scraper):
    """
    Arizona Event Scraper, gets interim committee, agendas, floor calendars
    and floor activity events
    """

    _tz = tmz("US/Arizona")

    _chamber_short = {"upper": "S", "lower": "H"}
    _chamber_long = {"upper": "Senate", "lower": "House"}

    def scrape(self, chamber=None):
        if chamber:
            if chamber == "other":
                return
            else:
                yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        """
        Scrape upper or lower committee agendas
        """
        # session = self.latest_session()
        # since we are scraping only latest_session
        # session_id = self.session_metadata.session_id_meta_data[session]

        # could use &ShowAll=ON doesn't seem to work though
        url = (
            "http://www.azleg.gov/CommitteeAgendas.asp?Body=%s"
            % self._chamber_short[chamber]
        )
        html_ = self.get(url).text
        doc = html.fromstring(html_)
        if chamber == "upper":
            event_table = doc.xpath(
                '//table[@id="body"]/tr/td/table[2]/' "tr/td/table/tr/td/table"
            )[0]
        else:
            event_table = doc.xpath(
                '//table[@id="body"]/tr/td/table[2]/tr'
                "/td/table/tr/td/table/tr/td/table"
            )[0]
        for row in event_table.xpath("tr")[2:]:
            # Agenda Date, Committee, Revised, Addendum, Cancelled, Time, Room,
            # HTML Document, PDF Document for house
            # Agenda Date, Committee, Revised, Cancelled, Time, Room,
            # HTML Document, PDF Document for senate
            text = [x.text_content().strip() for x in row.xpath("td")]
            when, committee = text[0:2]
            if chamber == "upper":
                time, room = text[4:6]
                link = row[6].xpath("string(a/@href)")
            else:
                time, room = text[5:7]
                link = row[7].xpath("string(a/@href)")
            if "NOT MEETING" in time or "CANCELLED" in time:
                continue
            time = re.match(r"(\d+:\d+ (A|P))", time)
            if time:
                when = "%s %sM" % (text[0], time.group(0))
                when = datetime.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
            else:
                when = text[0]
                when = datetime.datetime.strptime(when, "%m/%d/%Y")

            title = "Committee Meeting:\n%s %s %s\n" % (
                self._chamber_long[chamber],
                committee,
                room,
            )
            agenda_info = self.parse_agenda(chamber, link)

            description = agenda_info["description"]
            member_list = agenda_info["member_list"]
            related_bills = agenda_info["related_bills"]
            print(related_bills)
            """
            event = Event(session, when, 'committee:meeting', title,
                          location=room, link=link, details=description,
                          related_bills=related_bills)
            """
            event = Event(
                location_name=room,
                start_date=self._tz.localize(when),
                name=title,
                description=description,
            )
            event.add_participant(committee, type="committee", note="host")

            event.participants.extend(member_list)
            event.add_source(url)
            event.add_source(link)
            # print event['when'].timetuple()
            # import ipdb;ipdb.set_trace()
            yield event

    def parse_agenda(self, chamber, url):
        """
        parses the agenda detail and returns the description, participants, and
        any other useful info
        self.parse_agenda(url)--> (desc='', who=[], meeting_type='', other={})
        """
        html_ = self.get(url).text
        doc = html.fromstring(html_)

        # Related bills
        related_bills = []
        for tr in doc.xpath('//h3[contains(., "Bills")]/../../../../tr'):
            related_bill = {}
            bill_id = tr[1].text_content().strip()
            if not bill_id or bill_id[0] not in "HS":
                continue
            related_bill["bill_id"] = bill_id
            try:
                description = tr[3].text_content().strip()
            except IndexError:
                continue
            description = re.sub(r"\s+", " ", description)
            related_bill["description"] = description
            related_bill["type"] = "consideration"
            related_bills.append(related_bill)

        xpaths = ('//div[@class="Section1"]', '//div[@class="WordSection1"]')
        for xpath in xpaths:
            try:
                div = doc.xpath(xpath)[0]
            except IndexError:
                continue

        # probably committee + meeting_type?
        meeting_type = div.xpath("string(//p" '[contains(a/@name, "Joint_Meeting")])')
        members = doc.xpath('//p[contains(a/@name, "Members")]')
        if members:
            members = members[0]
        else:
            members = doc.xpath('//p[contains(span/a/@name, "Members")]')[0]
        other = {}
        member_list = []
        while members.tag == "p":
            text = members.text_content().strip().replace(u"\xa0", u" ")
            if text == "":
                break
            names = re.split(r"\s{5,}", text)
            if names:
                for name in names:
                    name = re.sub(r"\s+", " ", name)
                    if "," in name:
                        name, role = name.split(",")
                        role = role.lower()
                    else:
                        role = None
                    if name == "SENATORS" or name == "Members":
                        continue
                    if role in ["chair", "chairman"]:
                        role = "chair"
                    else:
                        role = "participant"
                    person = {
                        "type": role,
                        "participant": name,
                        "participant_type": "legislator",
                        "chamber": chamber,
                    }
                    member_list.append(person)
            members = members.getnext()
        description = ""
        agenda_items = div.xpath(
            '//p[contains(a/@name, "AgendaItems")]' "/following-sibling::table[1]"
        )
        if agenda_items:
            agenda_items = [
                tr.text_content().strip().replace("\r\n", "")
                for tr in agenda_items[0].getchildren()
                if tr.text_content().strip()
            ]
            description = ",\n".join(agenda_items)
        bill_list = div.xpath(
            '//p[contains(a/@name, "Agenda_Bills")]' "/following-sibling::table[1]"
        )
        if bill_list:
            try:
                bill_list = [
                    tr[1].text_content().strip()
                    + " "
                    + tr[3].text_content().strip().replace("\r\n", "")
                    for tr in bill_list[0].xpath("tr")
                    if tr.text_content().strip()
                ]
            except IndexError:
                bill_list = [
                    tr.text_content().strip().replace("\r\n", "")
                    for tr in bill_list[0].getchildren()
                    if tr.text_content().strip()
                ]

            bill_list = ",\n".join(bill_list)
            description = description + bill_list

        return {
            "description": description,
            "member_list": member_list,
            "meeting_type": meeting_type,
            "agenda_items": agenda_items,
            "related_bills": related_bills,
            "other": other,
        }

    """
    def scrape_interim_events(self, chamber, session):
        # Scrapes the events for interim committees
        session_id = self.get_session_id(session)
        url = 'http://www.azleg.gov/InterimCommittees.asp?Session_ID=%s' % session_id
        # common xpaths
        agendas_path = '//table[contains(' \
                       'tr/td/div[@class="ContentPageTitle"]/text(), "%s")]'

        html_ = self.get(url).text
        doc = html.fromstring(html_)
        table = doc.xpath(agendas_path % "Interim Committee Agendas")
        if table:
            rows = table[0].xpath('tr')
            for row in rows[2:]:
                pass
    """
