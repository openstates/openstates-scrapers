import pytz
import datetime
import dateutil.parser
import lxml
import requests
import re
import sys
from openstates.scrape import Scraper, Event


class INEventScraper(Scraper):
    _tz = pytz.timezone("America/Indianapolis")
    # avoid cloudflare blocks for no UA
    cf_headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    def scrape(self):
        list_url = 'http://iga.in.gov/legislative/2021/committees/standing'
        page = requests.get(list_url, headers=self.cf_headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url)

        for com_row in page.xpath('//li[contains(@class,"committee-item")]/a/@href'):
            print("LOOP")
            yield from self.scrape_committee_page(com_row)

    def scrape_committee_page(self, url):
        page = self.get(url, headers=self.cf_headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        com = page.xpath('//div[contains(@class, "pull-left span8")]/h1/text()')[0].strip()
        print(com)

        if com == "(S) Corrections and Criminal Law":
            sys.exit()

        for row in page.xpath('//div[contains(@id, "agenda-item")]'):
            status = 'tentative'
            meta = row.xpath('div[contains(@class,"accordion-heading-agenda")]/a')[0]

            date = meta.xpath('text()')[0].strip()

            time_and_loc = meta.xpath('span/text()')[0].strip()
            time_and_loc = "\n".split(time_and_loc)
            time = time_and_loc[0]
            loc = time_and_loc[1]

            print(time_and_loc)

            print(time, loc)

            if 'cancelled' in time.lower():
                continue



        yield {}

    #     chambers = [chamber] if chamber is not None else ["upper", "lower"]
    #     for chamber in chambers:
    #         yield from self.scrape_chamber(chamber)

    # def scrape_chamber(self, chamber):
    #     if chamber == "upper":
    #         url = "http://iga.in.gov/legislative/2021/committees/standing"
    #     elif chamber == "lower":
    #         url = "https://legislature.idaho.gov/sessioninfo/agenda/hagenda/"

    #     page = self.get(url).content
    #     page = lxml.html.fromstring(page)

    #     for row in page.xpath('//div[@id="ai1ec-container"]/div'):
    #         month = row.xpath(
    #             ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/text()"
    #         )[0].strip()
    #         day = row.xpath(
    #             ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/span/text()"
    #         )[0].strip()

    #         time_and_loc = row.xpath(
    #             ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'abbr')]/h2/text()"
    #         )
    #         time = time_and_loc[0].strip()
    #         loc = time_and_loc[1].strip()

    #         if "not meet" in time.lower():
    #             continue

    #         start = dateutil.parser.parse(f"{month} {day} {time}")
    #         start = self._tz.localize(start)

    #         com = row.xpath(
    #             ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'day')]/h2/a/text()"
    #         )[0].strip()

    #         event = Event(
    #             name=com,
    #             start_date=start,
    #             location_name=loc,
    #             classification="committee-meeting",
    #         )

    #         event.add_participant(com, type="committee", note="host")

    #         agenda_url = row.xpath('.//a[contains(text(), "Full Agenda")]/@href')[0]
    #         event.add_document("Agenda", agenda_url, media_type="application/pdf")

    #         agenda_rows = row.xpath(
    #             './/div[contains(@class,"card")]/div[contains(@id, "Agenda")]/div/table/tbody/tr'
    #         )[1:]

    #         for agenda_row in agenda_rows:
    #             subject = agenda_row.xpath("string(td[1])").strip()
    #             description = agenda_row.xpath("string(td[2])").strip()
    #             presenter = agenda_row.xpath("string(td[3])").strip()
    #             if presenter != "":
    #                 agenda_text = (
    #                     f"{subject} {description} Presenter: {presenter}".strip()
    #                 )
    #                 event.add_participant(agenda_text, type="person", note="Presenter")
    #             else:
    #                 agenda_text = f"{subject} {description}".strip()

    #             agenda = event.add_agenda_item(agenda_text)

    #             if agenda_row.xpath('td[1]/a[contains(@href,"/legislation/")]'):
    #                 agenda.add_bill(
    #                     agenda_row.xpath(
    #                         'td[1]/a[contains(@href,"/legislation/")]/text()'
    #                     )[0].strip()
    #                 )

    #         event.add_source(url)
    #         yield event
