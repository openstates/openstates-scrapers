import re
import datetime as dt

from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html

url = "http://assembly.state.ny.us/leg/?sh=hear"


class NYAssemblyEventScraper(EventScraper):
    _tz = pytz.timezone('US/Eastern')
    jurisdiction = 'ny'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def parse_page(self, url, session):
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

            try:
                datetime = dt.datetime.strptime(date, "%B %d %Y %I:%M %p")
            except ValueError:
                datetime = dt.datetime.strptime(date, "%b. %d %Y %I:%M %p")

            event = Event(session, datetime, 'committee:meeting',
                          metainf['Public Hearing:'],
                          location=metainf['Place:'],
                          contact=metainf['Contact:'],
                          media_contact=metainf['Media Contact:'])
            event.add_source(url)
            event.add_participant('host',
                                  ctty,
                                  'committee',
                                  chamber=chamber)

            self.save_event(event)

    def scrape(self, chamber, session):
        if chamber == 'other':
            self.parse_page(url, session)


class NYSenateEventScraper(EventScraper):
    _tz = pytz.timezone('US/Eastern')
    jurisdiction = 'ny'
    crappy = []

    def scrape(self, chamber, session):
        if chamber != 'upper':
            return

        url = (r'http://open.nysenate.gov/legislation/2.0/search.json?'
               r'term=otype:meeting&pageSize=1000&pageIdx=%d')
        page_index = 1
        while True:
            resp = self.urlopen(url % page_index)
            if not resp.response.json['response']['results']:
                break
            for obj in resp.response.json['response']['results']:
                event = self.scrape_event(chamber, session, obj)
                if event:
                    self.save_event(event)
            page_index += 1

    def scrape_event(self, chamber, session, obj):
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
