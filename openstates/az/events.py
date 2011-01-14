from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

from lxml import html
import datetime, re
import pytz

class AZEventScraper(EventScraper):
    """
    Arizona Event Scraper, gets interim committee, agendas, floor calendars
    and floor activity events
    """
    state = 'az'
    _tz = pytz.timezone('US/Arizona')
    
    _chamber_short = {'upper': 'S', 'lower': 'H'}
    _chamber_long = {'upper': 'Senate', 'lower': 'House'}
    
    def get_session_id(self, session):
        """
        returns the session id for a given session
        """
        return self.metadata['session_details'][session]['session_id']
        
    def scrape(self, chamber, session):
        """
        given a chamber and session returns the events
        """
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)
            
        # this will only work on the latest regular or special session
        # 103 is fortyninth - ninth special session 102 is session_ID for
        # fiftieth
        # we can get old events with some hassle but we cant change what has 
        # already happened so why bother?
        if session_id == 103 or session_id < 102:
            raise NoDataForPeriod(session)
            
        # http://www.azleg.gov/CommitteeAgendas.asp?Body=H
        self.scrape_committee_agendas(chamber, session)
        # http://www.azleg.gov/InterimCommittees.asp
        # self.scrape_interim_events(chamber, session)
            
    def scrape_committee_agendas(self, chamber, session):
        """
        Scrape upper or lower committee agendas
        """
        # could use &ShowAll=ON doesn't seem to work though
        url = 'http://www.azleg.gov/CommitteeAgendas.asp?Body=%s' % \
                                          self._chamber_short[chamber]
        with self.urlopen(url) as agendas:
            root = html.fromstring(agendas)
            if chamber == 'upper':
                event_table = root.xpath('//table[@id="body"]/tr/td/table[2]/tr'
                                         '/td/table/tr/td/table')[0]
            else:
                event_table = root.xpath('//table[@id="body"]/tr/td/table[2]/tr'
                                         '/td/table/tr/td/table/tr/td/table')[0]
            for row in event_table.xpath('tr')[2:]:
                # Agenda Date, Committee, Revised, Addendum, Cancelled, Time, Room,
                # HTML Document, PDF Document for house
                # Agenda Date, Committee, Revised, Cancelled, Time, Room,
                # HTML Document, PDF Document for senate
                text = [ x.text_content().strip() for x in row.xpath('td') ]
                when, committee = text[0:2]
                if chamber == 'upper':
                    time, room = text[4:6]
                    link = row[6].xpath('string(a/@href)')
                else:
                    time, room = text[5:7]
                    link = row[7].xpath('string(a/@href)')
                if 'NOT MEETING' in time or 'CANCELLED' in time:
                    continue
                time = re.match('(\d+:\d+ (A|P))', time)
                if time:
                    when = "%s %sM" % (text[0], time.group(0))
                    when = datetime.datetime.strptime(when, '%m/%d/%Y %I:%M %p')
                else:
                    when = text[0]
                    when = datetime.datetime.strptime(when, '%m/%d/%Y')
                    
                when = self._tz.localize(when)
                
                title = "Committee Meeting:\n%s %s %s\n" % (
                                                  self._chamber_long[chamber], 
                                                  committee, room)
                (description, member_list, 
                 meeting_type, other) = self.parse_agenda(chamber, link)
                event = Event(session, when, 'committee:meeting', title,
                              location=room, link=link, details=description)
                event.add_participant('committee', committee)
                event['participants'].extend(member_list)
                event.add_source(url)
                event.add_source(link)
                self.save_event(event)
                
    def parse_agenda(self, chamber, url):
        """
        parses the agenda detail and returns the description, participants, and
        any other useful info
        self.parse_agenda(url)--> (desc='', who=[], meeting_type='', other={})
        """
        with self.urlopen(url) as agenda_detail:
            root = html.fromstring(agenda_detail)
            div = root.xpath('//div[@class="Section1"]')[0]
            # probably committee + meeting_type?
            meeting_type = div.xpath('string(//p'
                                     '[contains(a/@name, "Joint_Meeting")])')
            members = root.xpath('//p[contains(a/@name, "Members")]')
            if members:
                members = members[0]
            else:
                members = root.xpath('//p[contains(span/a/@name, "Members")]')[0]
            if chamber == 'lower':
                name_role = re.compile(r'(\w+.\s\w+\s?[a-zA-z]*(?!<.))'
                                        ',?\s?(\w+-?\w+)?')
            else:
                name_role = re.compile(r'(\w+),?\s*(\w+-?\w+)?')
            other = {}
            member_list = []
            while members.tag == 'p':
                text = members.text_content().strip()
                if text == '': break
                found = name_role.findall(text)
                if found:
                    for name, role in found:
                        if name == 'SENATORS' or name == 'Members': continue
                        person = {"type": role or "member", "participant": name}
                        member_list.append(person)
                members = members.getnext()
            description = ""
            agenda_items = div.xpath('//p[contains(a/@name, "AgendaItems")]'
                                    '/following-sibling::table[1]')
            if agenda_items:
                agenda_items = [tr.text_content().strip().replace("\r\n", "") 
                                for tr in agenda_items[0].getchildren()
                                if tr.text_content().strip()]
                description = ",\n".join(agenda_items)
            bill_list = div.xpath('//p[contains(a/@name, "Agenda_Bills")]'
                                    '/following-sibling::table[1]')
            if bill_list:
                bill_list = [tr[1].text_content().strip() + " " + 
                             tr[3].text_content().strip().replace("\r\n", "") 
                             for tr in bill_list[0].xpath('tr')
                             if tr.text_content().strip()]
                bill_list = ",\n".join(bill_list)
                description = description + bill_list
            return (description, member_list, meeting_type, other)
        
    def scrape_interim_events(self, chamber, session):
        """
        Scrapes the events for interim committees
        """
        session_id = self.get_session_id(session)
        url = 'http://www.azleg.gov/InterimCommittees.asp?Session_ID=%s' % session_id
        # common xpaths
        agendas_path = '//table[contains(' \
                       'tr/td/div[@class="ContentPageTitle"]/text(), "%s")]'
        
        with self.urlopen(url) as event_page:
            root = html.fromstring(event_page)
            table = root.xpath(agendas_path % "Interim Committee Agendas")
            if table:
                rows = table[0].xpath('tr')
                for row in rows[2:]:
                    pass
