import re
import dateutil.parser
import pytz
import lxml.html
import requests
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from utils.events import match_coordinates


class OKEventScraper(Scraper):
    _tz = pytz.timezone("CST6CDT")
    session = requests.Session()

    def scrape(self, chamber=None):

        # we need to GET the page once to set up the ASP.net vars
        # then POST to it to set it to monthly
        url = "https://www.okhouse.gov/Committees/MeetingNotices.aspx"

        params = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$cbMonthly",
            "ctl00$ScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$cbMonthly",
            "ctl00_FormDecorator1_ClientState": "",
            "ctl00_RadToolTipManager1_ClientState": "",
            "ctl00_mainNav_ClientState": "",
            "ctl00$ContentPlaceHolder1$cbToday": "on",
            "ctl00$ContentPlaceHolder1$cbMonthly": "on",
            "ctl00_ContentPlaceHolder1_dgrdNotices_ClientState": "",
            "__ASYNCPOST": "true",
            "RadAJAXControlID": "ctl00_ContentPlaceHolder1_RadAjaxPanel1",
        }

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        html = self.asp_post(url, page, params)
        page = lxml.html.fromstring(html)
        event_count = 0

        for row in page.xpath('//tr[contains(@id,"_dgrdNotices_")]'):
            status = "tentative"
            agenda_link = row.xpath('.//a[@id="hlMeetAgenda"]')[0]
            title = agenda_link.xpath("text()")[0].strip()
            agenda_url = agenda_link.xpath("@href")[0]
            location = row.xpath("td[3]")[0].text_content().strip()

            if re.match(r"^room [\w\d]+$", location, flags=re.I) or re.match(
                r"senate room [\w\d]+$", location, flags=re.I
            ):
                location = f"{location} 2300 N Lincoln Blvd, Oklahoma City, OK 73105"

            # swap in a space for the <br/>
            when = row.xpath("td[4]")[0]
            for br in when.xpath(".//br"):
                br.tail = " " + br.tail if br.tail else " "

            when = when.text_content().strip()
            if "cancelled" in when.lower():
                status = "cancelled"

            when = re.sub("CANCELLED", "", when, re.IGNORECASE)
            when = self._tz.localize(dateutil.parser.parse(when))

            event = Event(
                name=title,
                location_name=location,
                start_date=when,
                classification="committee-meeting",
                status=status,
            )

            event.add_source(url)

            event.add_committee(title, note="host")

            event.add_document("Agenda", agenda_url, media_type="application/pdf")

            match_coordinates(event, {"2300 N Lincoln Blvd": (35.49293, -97.50311)})

            event_count += 1
            yield event

        if event_count < 1:
            raise EmptyScrape

    def asp_post(self, url, page, params):
        page = self.session.get(url)
        page = lxml.html.fromstring(page.content)
        (viewstate,) = page.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = page.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = page.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        (scriptmanager,) = page.xpath('//input[@id="ctl00_ScriptManager1_TSM"]/@value')

        headers = {
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
            "x-microsoftajax": "Delta=true",
            "referer": "https://www.okhouse.gov/Committees/MeetingNotices.aspx",
            "origin": "https://www.okhouse.gov",
        }

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
        }

        form = {**form, **params}

        response = self.session.post(url, form, headers=headers).content
        return response
