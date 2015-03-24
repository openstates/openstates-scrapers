import datetime as dt

from billy.scrape.events import Event, EventScraper
from openstates.utils import LXMLMixin
import scrapelib
import pytz


calurl = "http://committeeschedule.legis.wisconsin.gov/?filter=Upcoming&committeeID=-1"

class WIEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'wi'
    _tz = pytz.timezone('US/Eastern')

    def scrape_participants(self, session, href):
        try:
            page = self.lxmlize(href)
        except scrapelib.HTTPError:
            self.warning("Committee page not found for this event")
            return []

        legs = page.xpath("//a[contains(@href, '/Pages/leg-info.aspx')]/text()")
        role_map = {"participant": "participant",
                    "Chair": "chair",
                    "Co-Chair": "chair",
                    "Vice-Chair": "participant"}
        ret = []
        for leg in legs:
            name = leg
            title = 'participant'
            if "(" and ")" in leg:
                name, title = leg.split("(", 1)
                title = title.replace(")", " ").strip()
                name = name.strip()
            title = role_map[title]
            ret.append({
                "name": name,
                "title": title
            })
        return ret

    def scrape(self, session, chambers):
        page = self.lxmlize(calurl)
        events = page.xpath("//table[@class='agenda-body']//tr")[1:]

        for event in events:
            comit_url = event.xpath(
                ".//a[contains(@href, '/Pages/comm-info.aspx?c=')]")

            if len(comit_url) != 1:
                raise Exception

            comit_url = comit_url[0]
            who = self.scrape_participants(session, comit_url.attrib['href'])

            tds = event.xpath("./*")
            date = tds[0].text_content().strip()
            cttie = tds[1].text_content().strip()
            cttie_chamber, cttie = [x.strip() for x in cttie.split(" - ", 1)]
            info = tds[2]
            name = info.xpath("./a[contains(@href, 'raw')]")[0]
            notice = name.attrib['href']
            name = name.text
            time, where = info.xpath("./i/text()")
            what = tds[3].text_content()
            what = what.replace("Items: ", "")
            if "(None)" in what:
                continue
            what = [x.strip() for x in what.split(";")]

            when = ", ".join([date, str(dt.datetime.now().year), time])
            when = dt.datetime.strptime(when, "%a %b %d, %Y, %I:%M %p")

            event = Event(session, when, 'committee:meeting', name,
                          location=where, link=notice)

            event.add_source(calurl)
            event.add_participant('host', cttie, 'committee',
                                  chamber=cttie_chamber)
            event.add_document("notice", notice, mimetype='application/pdf')

            for thing in who:
                event.add_participant(thing['title'], thing['name'],
                                      'legislator', chamber=cttie_chamber)

            self.save_event(event)
