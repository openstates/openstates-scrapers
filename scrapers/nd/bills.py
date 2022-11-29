import logging
import re
import requests
import lxml.html
import time
import random
import datetime as dt
from openstates.scrape import Scraper, Bill
from spatula import HtmlListPage, HtmlPage, XPath, CSS


def random_sleep(avg_secs):
    inverse_frequency = round(7 * avg_secs)
    duration = 14 * random.random() * avg_secs
    if random.randint(1, inverse_frequency) == 1:
        print(f"Sleeping for {round(duration, 2)} seconds...")
        time.sleep(duration)


def get_committee_names(session):
    source = f"http://www.ndlegis.gov/assembly/{session}/committees"
    response = requests.get(source)
    content = lxml.html.fromstring(response.content)
    committee_names = set()
    committees = content.xpath(".//div[@class='grouping-wrapper']//a/text()")
    for committee in committees:
        committee_names.add(committee.strip())
    return committee_names


class BillList(HtmlListPage):
    url_session = "67-2021"
    session_components = url_session.split("-")
    source = f"http://www.ndlegis.gov/assembly/{url_session}/bill-index.html"
    selector = XPath(".//div[@class='col bill']")
    committees = get_committee_names(url_session)

    def process_item(self, item):
        bill_id_elem = CSS(".bill-name").match(item)[0]
        bill_id = bill_id_elem.text_content().strip()
        print(bill_id)

        bill_type_abbr = bill_id[0:3].strip()
        bill_type = "bill"
        if bill_type_abbr in ("HR", "SR"):
            bill_type = "resolution"
        if bill_type_abbr in ("HCR", "SCR"):
            bill_type = "concurrent resolution"
        if bill_type_abbr in ("HMR", "SMR"):
            bill_type = "memorial"

        bill_url = CSS(".card-link").match(item)[0].get("href")

        bill_card = CSS(".card-body").match(item)[0]
        title = bill_card.xpath(".//p")[0].text_content().strip()

        bill = Bill(
            bill_id,
            self.session_components[1],
            title,
            chamber="lower" if bill_id[0] == "H" else "upper",
            classification=bill_type,
        )

        bill.add_source(bill_url)

        sponsors_div = bill_card.xpath(".//div[@class='sponsors scroll']")[0]
        sponsors_text = sponsors_div.text_content().split("Introduced by")[1].strip()
        if ", " in sponsors_text:
            sponsors_list = sponsors_text.split(", ")
        else:
            sponsors_list = [sponsors_text]
        for sponsor in sponsors_list:
            if sponsor in self.committees:
                entity_type = "organization"
            else:
                entity_type = "person"
            bill.add_sponsorship(
                sponsor,
                classification="cosponsor",
                entity_type=entity_type,
                primary=False,
            )
        return BillDetail(bill)


class BillDetail(HtmlPage):
    input_type = Bill
    example_input = Bill(
        "HB 1001",
        "2021",
        "[title]",
        chamber="lower",
        classification="bill",
    )

    def get_source_from_input(self):
        return self.input.sources[0]["url"]

    def process_page(self):
        random_sleep(0.5)
        self.process_versions()
        random_sleep(0.5)
        self.process_actions()
        yield self.input

    def process_versions(self):
        source = re.sub("overview/bo", "index/bi", self.source.url)
        response = requests.get(source)
        content = lxml.html.fromstring(response.content)

        version_rows = content.xpath(".//table[@id='version-table']/tbody//tr")
        for row in version_rows:
            vers_links = row.xpath("td[1]//a")

            for link in vers_links:
                name = row.xpath("td[2]/text()")
                if name:
                    (name,) = name
                else:
                    (name,) = link.xpath("text()")

                type_badge = link.xpath("span[@data-toggle='tooltip']")
                if type_badge:
                    (vers_type,) = type_badge[0].xpath("@title")
                    if vers_type.strip() == "Marked up":
                        name += "(Marked up)"
                else:
                    vers_type = None

                (href,) = link.xpath("@href")
                url = re.sub("/bill-index.+", href[2:], source)

                if not vers_type or vers_type.strip() == "Engrossment":
                    self.input.add_version_link(note=name, url=url, media_type="pdf")
                else:
                    self.input.add_document_link(note=name, url=url, media_type="pdf")

    def process_actions(self):
        source = re.sub("overview/bo", "actions/ba", self.source.url)
        response = requests.get(source)
        content = lxml.html.fromstring(response.content)

        action_rows = content.xpath(".//table[@id='action-table']/tbody//tr")
        for row in action_rows:
            (action,) = row.xpath("td[3]/text()")

            actor = "legislature"
            chambers_dict = {"House": "lower", "Senate": "upper"}
            chamber = row.xpath("td[2]/text()")
            if chamber:
                chamber = chamber[0].strip()
                if chamber in chambers_dict.keys():
                    actor = chambers_dict[chamber]
            if "governor" in action.lower():
                actor = "executive"

            (date,) = row.xpath("td[1]/b/text()")
            date += f"/{self.input.legislative_session}"
            date = dt.datetime.strptime(date, "%m/%d/%Y")

            self.input.add_action(
                action,
                date.strftime("%Y-%m-%d"),
                chamber=actor,
                classification="introduction",
            )


class NDBillScraper(Scraper):
    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
