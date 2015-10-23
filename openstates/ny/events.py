import re
import datetime as dt
import pytz
import lxml.html
from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin

url = "http://assembly.state.ny.us/leg/?sh=hear"


class NYEventScraper(EventScraper, LXMLMixin):
    _tz = pytz.timezone('US/Eastern')
    jurisdiction = 'ny'

    def lower_parse_page(self, url, session):
        page = self.lxmlize(url)
        tables = page.xpath("//table[@class='pubhrgtbl']")
        date = None
        ctty = None
        chamber = 'other'
        for table in tables:
            metainf = {}
            rows = table.xpath(".//tr")
            for row in rows:
                tds = row.xpath("./*")
                if len(tds) < 2:
                    continue
                key, value = tds
                if key.tag == 'th':
                    date = key.text_content()
                    date = re.sub("\s+", " ", date)
                    date = re.sub(".*POSTPONED NEW DATE", "", date).strip()
                    ctty = value.xpath(".//strong")[0]
                    ctty = ctty.text_content()

                    chamber = 'other'
                    if "senate" in ctty.lower():
                        chamber = 'upper'
                    if "house" in ctty.lower():
                        chamber = 'lower'
                    if "joint" in ctty.lower():
                        chamber = 'joint'
                elif key.tag == 'td':
                    key = key.text_content().strip()
                    value = value.text_content().strip()
                    value = value.replace(u'\x96', '-')
                    value = re.sub("\s+", " ", value)
                    metainf[key] = value

            time = metainf['Time:']
            repl = {
                "A.M.": "AM",
                "P.M.": "PM",
            }
            drepl = {
                "Sept": "Sep"
            }
            for r in repl:
                time = time.replace(r, repl[r])

            for r in drepl:
                date = date.replace(r, drepl[r])

            time = re.sub("-.*", "", time)
            time = time.strip()

            year = dt.datetime.now().year

            date = "%s %s %s" % (
                date,
                year,
                time
            )

            if "tbd" in date.lower():
                continue

            date = date.replace(' PLEASE NOTE NEW TIME', '')

            # Check if the event has been postponed.
            postponed = 'POSTPONED' in date
            if postponed:
                date = date.replace(' POSTPONED', '')

            date_formats = ["%B %d %Y %I:%M %p", "%b. %d %Y %I:%M %p"]
            datetime = None
            for fmt in date_formats:
                try:
                    datetime = dt.datetime.strptime(date, fmt)
                except ValueError:
                    pass

            # If the datetime can't be parsed, bail.
            if datetime is None:
                return

            title_key = set(metainf) & set([
                'Public Hearing:', 'Summit:', 'Roundtable:',
                'Public Roundtable:', 'Public Meeting:', 'Public Forum:',
                'Meeting:'])
            assert len(title_key) == 1, "Couldn't determine event title."
            title_key = list(title_key).pop()
            title = metainf[title_key]

            title = re.sub(
                    r"\*\*Click here to view public hearing notice\*\*",
                    "",
                    title
                    )

            # If event was postponed, add a warning to the title.
            if postponed:
                title = 'POSTPONED: %s' % title

            event = Event(session, datetime, 'committee:meeting',
                          title,
                          location=metainf['Place:'],
                          contact=metainf['Contact:'])
            if 'Media Contact:' in metainf:
                event.update(media_contact=metainf['Media Contact:'])
            event.add_source(url)
            event.add_participant('host',
                                  ctty,
                                  'committee',
                                  chamber=chamber)

            self.save_event(event)

    def scrape(self, chamber, session):
        self.scrape_lower(chamber, session)
        #self.scrape_upper(chamber, session)

    def scrape_lower(self, chamber, session):
        if chamber == 'other':
            self.lower_parse_page(url, session)

    """
    def scrape_upper(self, chamber, session):
        if chamber != 'upper':
            return

        url = (r'http://open.nysenate.gov/legislation/2.0/search.json?'
               r'term=otype:meeting&pageSize=1000&pageIdx=%d')
        page_index = 1
        while True:
            resp = self.get(url % page_index)
            if not resp.json():
                break
            if not resp.json()['response']['results']:
                break
            for obj in resp.json()['response']['results']:
                event = self.upper_scrape_event(chamber, session, obj)
                if event:
                    self.save_event(event)
            page_index += 1

    def upper_scrape_event(self, chamber, session, obj):
        meeting = obj['data']['meeting']
        date = int(meeting['meetingDateTime'])
        date = dt.datetime.fromtimestamp(date / 1000)
        if str(date.year) not in session:
            return
        description = 'Committee Meeting: ' + meeting['committeeName']
        event = Event(session, date, 'committee:meeting',
                      description=description,
                      location=meeting['location'] or 'No location given.')
        event.add_source(obj['url'])
        event.add_participant('chair', meeting['committeeChair'],
                              'legislator', chamber='upper')
        event.add_participant('host', meeting['committeeName'],
                              'committee', chamber='upper')

        rgx = r'([a-z]+)(\d+)'
        for bill in meeting['bills']:
            raw_id = bill['senateBillNo']
            bill_id = ' '.join(re.search(rgx, raw_id, re.I).groups())
            event.add_related_bill(
                bill_id, type='bill',
                description=bill['summary'] or 'No description given.')
        return event
        """
