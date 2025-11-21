# import datetime as dt
import dateutil
import re
import lxml.html

# import scrapelib
# import json
# import math
import pytz
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.data.common import VOTE_OPTIONS
from utils import LXMLMixin

from .actions import Categorizer

CO_URL_BASE = "https://leg.colorado.gov"

CHAMBERS = {
    "upper": "Senate",
    "lower": "House",
}

ACTION_CHAMBERS = {
    "Senate": "upper",
    "House": "lower",
    "Governor": "executive",
    "Joint": "joint",
}

BILL_CHAMBERS = {
    "H": "lower",
    "S": "upper",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


class COBillScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Mountain")
    categorizer = Categorizer()
    session_name = ""
    bill_year = ""
    page_number = 1
    max_pages = 2

    def scrape(self, chamber=None, session=None):
        # TODO: there's a better way to do this
        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                self.session_name = i["_scraped_name"]
                # we need this for session laws
                self.bill_year = str(dateutil.parser.parse(i["start_date"]).year)

        while self.page_number <= self.max_pages:
            yield from self.scrape_bill_list(
                session, self.session_name, self.page_number, chamber
            )

    def scrape_bill_list(
        self, session: str, session_name: str, pageNumber: int = 1, chamber: str = None
    ):
        self.info(f"Scraping page {self.page_number}")
        url = "https://leg.colorado.gov/bills/bill-search"
        data = {
            "q": "",
            "sessions[]": session_name,
            "show_filters": "",
            "sort": "Last Action Descending",
            "page": pageNumber,
        }

        if chamber:
            data["chambers[]"] = CHAMBERS[chamber]

        page = self.post(url, data=data, headers=HEADERS).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        self.max_pages = int(page.cssselect("button[data-page]")[-1].text_content())

        for row in page.cssselect("a.all-bills-data-heading"):
            yield from self.scrape_bill(row.xpath("@href")[0], session)

        self.page_number += 1

    def clean(self, text):
        if type(text) is list:
            return text[0].text_content().strip()
        return text.text_content().strip()

    def scrape_bill(self, url: str, session: str):
        page = self.get(url, headers=HEADERS).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_title = self.clean(page.cssselect("div.full-bill-topic h1"))
        bill_number = self.clean(page.cssselect("span.bill-detail-bill-number-tag"))

        # convert from SB25-300 or SB24B-300 to SB 300
        match = re.search(r"\d+[A-Z]?\-", bill_number, re.IGNORECASE)
        if match:
            parts = bill_number.split(match.group(0))
            bill_number = f"{parts[0]} {parts[1]}"

        chamber = BILL_CHAMBERS[bill_number[0:1]]

        bill = Bill(
            bill_number, legislative_session=session, chamber=chamber, title=bill_title
        )

        summary_elems = page.cssselect("div.bill-detail-bill-summary")
        # Some bills do not have a summary shown on the page
        if len(summary_elems) > 0:
            summary = summary_elems[0].text_content().strip()
            bill.add_abstract(summary, "summary")

        self.scrape_actions(bill, page)
        self.scrape_amendments(bill, page)
        self.scrape_documents(bill, page)
        self.scrape_laws(bill, page)
        self.scrape_sponsors(bill, page)
        self.scrape_subjects(bill, page)
        self.scrape_versions(bill, page)

        yield from self.scrape_votes(bill, page, chamber)

        bill.add_source(url)

        yield bill

    def scrape_actions(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect("div#bill-histories tbody tr"):
            action_date = dateutil.parser.parse(
                self.clean(row.xpath("td[1]/span"))
            ).date()
            actor = self.clean(row.xpath("td[2]/span"))

            if actor == "ConfComm":
                actor = "Joint"

            actor = ACTION_CHAMBERS[actor]
            action_text = self.clean(row.xpath("td[3]/span"))

            action_class = self.categorizer.categorize(action_text)

            action = bill.add_action(
                action_text,
                action_date,
                chamber=actor,
                classification=action_class["classification"],
            )

            if "committees" in action_class:
                for com in action_class["committees"]:
                    action.add_related_entity(com, entity_type="organization")

    def scrape_amendments(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect("div#bill-activity-amendments tbody tr"):
            title = self.clean(row.xpath("td[2]/span"))
            title = f"Amendment {title}"
            published = dateutil.parser.parse(
                self.clean(row.xpath("td[1]/span"))
            ).date()
            bill.add_document_link(
                title,
                row.xpath("td[5]/span/a/@href")[0],
                date=published,
                media_type="application/pdf",
            )

    def scrape_documents(self, bill: Bill, page: lxml.html.HtmlElement):
        # committee reports
        for row in page.xpath("//a[contains(text(), 'Committee Report')]"):
            title = row.xpath("@aria-label")[0].replace("View ", "").strip()
            url = row.xpath("@href")[0].strip()
            bill.add_document_link(
                title,
                url,
                media_type="text/html",
                classification="committee-report",
            )

            if row.xpath("span/a[contains(@class,'ext-link-pdf')]"):
                bill.add_document_link(
                    title,
                    row.xpath("span/a[contains(@class,'ext-link-pdf')]")[0].strip(),
                    media_type="application/pdf",
                    classification="committee-report",
                )

        # fiscal notes
        for row in page.cssselect("div#bill-files-fiscal tbody tr"):
            title = self.clean(row.xpath("td[2]/span"))
            title = title.replace("FN", "Fiscal Note ")
            published = dateutil.parser.parse(
                self.clean(row.xpath("td[1]/span"))
            ).date()
            bill.add_document_link(
                title,
                row.xpath("td[3]/span/a/@href")[0],
                date=published,
                media_type="application/pdf",
                classification="fiscal-note",
            )

    def scrape_laws(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect("div#bill-activity-session-laws tbody tr"):
            effective = dateutil.parser.parse(
                self.clean(row.xpath("td[1]/span"))
            ).date()
            chapter = self.clean(row.xpath("td[2]/span"))
            title = self.clean(row.xpath("td[3]/span"))
            chapter = f"Chapter: {chapter} {title}"
            url = row.xpath("td[4]//a/@href")[0]

            bill.add_citation(
                f"Colorado Session Laws of {self.bill_year}",
                chapter,
                citation_type="chapter",
                effective=effective,
                url=url,
            )

    def scrape_sponsors(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect(
            "div.bill-detail-prime div.sponsor-link a, div.bill-detail-additional-sponsor div.sponsor-link a"
        ):
            sponsor = self.clean(row)
            chamber = "upper" if "Sen." in sponsor else "lower"
            sponsor = sponsor.replace("Sen.", "").replace("Rep.", "")
            bill.add_sponsorship(
                sponsor,
                classification="sponsor",
                entity_type="person",
                primary=True,
                chamber=chamber,
            )
        for row in page.cssselect("div.bill-detail-co-sponsor div.sponsor-link a"):
            sponsor = self.clean(row)
            chamber = "upper" if "Sen." in sponsor else "lower"
            sponsor = sponsor.replace("Sen.", "").replace("Rep.", "")
            bill.add_sponsorship(
                sponsor,
                classification="cosponsor",
                entity_type="person",
                primary=False,
                chamber=chamber,
            )

    def scrape_subjects(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect("span.subject-tag"):
            subject = self.clean(row)
            bill.add_subject(subject)

    def scrape_versions(self, bill: Bill, page: lxml.html.HtmlElement):
        for row in page.cssselect("div#bill-files-all-versions tbody tr"):
            title = self.clean(row.xpath("td[2]/span"))
            published = dateutil.parser.parse(
                self.clean(row.xpath("td[1]/span"))
            ).date()
            bill.add_version_link(
                title,
                row.xpath("td[3]/span/a/@href")[0],
                date=published,
                media_type="application/pdf",
            )

            if row.xpath("td[2]/span/a"):
                bill.add_version_link(
                    title,
                    row.xpath("td[2]/span/a/@href")[0],
                    date=published,
                    media_type="text/html",
                )

    def scrape_votes(self, bill: Bill, page: lxml.html.HtmlElement, chamber: str):
        # committee votes are slightly differently formatted
        for parent in page.cssselect("div#bill-activity-committees div.gen-accordion"):
            when = parent.cssselect("button h4")[0].text_content().split("|")[0]
            when = dateutil.parser.parse(when, fuzzy=True).date()
            chamber = "upper" if "Senate" in parent.text_content() else "lower"

            for row in parent.cssselect("tbody tr"):
                motion = self.clean(row.xpath("td[1]/span"))
                result_text = self.clean(row.xpath("td[2]/span"))
                vote = VoteEvent(
                    chamber=chamber,
                    start_date=when,
                    motion_text=motion,
                    result="pass" if "passed" in result_text else "fail",
                    bill=bill,
                    classification="passage",
                )
                votes_url = row.xpath("td[3]/span/a/@href")[0]
                votes_page = self.get(votes_url, headers=HEADERS).content
                votes_page = lxml.html.fromstring(votes_page)

                for vote_row in votes_page.cssselect(
                    "div.standard-table div.col-12:nth-of-type(2) table.table tr"
                ):
                    vote_option = self.clean(
                        vote_row.cssselect("span.vote-tag")
                    ).lower()

                    if "voice vote" not in vote_option.lower():
                        if vote_option not in VOTE_OPTIONS:
                            self.info(
                                f"Couldn't find {vote_option} in choices, setting to other."
                            )
                            vote_option = "other"
                        vote.vote(
                            vote_option,
                            self.clean(vote_row.xpath("td[1]")),
                        )

                vote.add_source(votes_url)
                yield vote

        for row in page.cssselect("div#bill-votes-first-chamber tbody tr"):
            when = dateutil.parser.parse(self.clean(row.xpath("td[1]/span"))).date()
            motion = self.clean(row.xpath("td[3]/span"))
            ct_yes = int(self.clean(row.cssselect(".bill-votes-count-yes")))
            ct_no = int(self.clean(row.cssselect(".bill-votes-count-no")))
            ct_other = int(self.clean(row.cssselect(".bill-votes-count-others")))
            chamber = "upper" if "Senate" in row.text_content() else "lower"

            vote = VoteEvent(
                chamber=chamber,
                start_date=when,
                motion_text=motion,
                result="pass" if ct_yes > (ct_no + ct_other) else "fail",
                bill=bill,
                classification="passage",
            )

            votes_url = row.xpath("td[5]/span/a/@href")[0]
            votes_page = self.get(votes_url, headers=HEADERS).content
            votes_page = lxml.html.fromstring(votes_page)

            vote.add_source(votes_url)
            for vote_row in votes_page.cssselect(
                "div.standard-table div.col-12:nth-of-type(2) table.table tr"
            ):
                vote_option = self.clean(vote_row.cssselect("span.vote-tag")).lower()
                if "voice vote" not in vote_option.lower():
                    if vote_option not in VOTE_OPTIONS:
                        self.info(
                            f"Couldn't find {vote_option} in choices, setting to other."
                        )
                        vote_option = "other"
                    vote.vote(
                        vote_option,
                        self.clean(vote_row.xpath("td[1]")),
                    )

            yield vote
