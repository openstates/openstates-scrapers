import cloudscraper
import dateutil
import lxml.html
import pytz
import re

from openstates.scrape import Scraper, Bill


class MPBillScraper(Scraper):
    _tz = pytz.timezone("Pacific/Guam")

    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }

    bill_types = {
        "Senate Resolutions:": "SR",
        "Senate Bills:": "SB",
        "Senate Legislative initiatives:": "SLI",
        "Senate Joint Resolutions:": "SJR",
        "Senate Local Bills:": "SLB",
        "Senate Commemorative Resolutions:": "SR",
    }

    bill_type_map = {
        "HB": "bill",
        "SB": "bill",
        "HR": "resolution",
        "SR": "resolution",
        "HLB": "bill",
        "SLB": "bill",
        "HJR": "joint resolution",
        "SJR": "joint resolution",
        "HCR": "concurrent resolution",
        "HLI": "bill",
        "SLI": "bill",
        "HLB": "bill",
        "SLB": "bill",
        "HCommRes": "resolution",
    }

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber else ["upper", "lower"]
        # throwaway request to get our session cookies before the POST
        self.scraper.get("https://cnmileg.net/house.asp")

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):

        sec_ids = {"upper": "2", "lower": "1"}
        data = {
            "legtypeID": "A",
            "submit": "Go",
            "legsID": session,
            "secID": sec_ids[chamber],
        }
        self.info("POST https://cnmileg.net/leglist.asp")

        page = self.scraper.post("https://cnmileg.net/leglist.asp", data=data).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute("https://cnmileg.net/")

        for row in page.xpath("//table/tr")[1:]:
            bill_url = row.xpath("td[4]/a/@href")[0]
            yield from self.scrape_bill(session, chamber, bill_url)

    def scrape_bill(self, session, chamber, url):
        self.info(f"GET {url}")
        page = self.scraper.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_id = self.get_cell_text(page, "Number")

        if chamber == "upper":
            bill_type = page.xpath("//tr[@class='stshead']/th/text()")[0].strip()
            bill_type = self.bill_types[bill_type]
            bill_id = f"{bill_type} {bill_id}"

        title = self.get_cell_text(page, "Subject/Title")

        bill_type = self.bill_type_map[bill_id.split(" ")[0]]

        bill = Bill(
            identifier=bill_id,
            title=title,
            legislative_session=session,
            chamber=chamber,
            classification=bill_type,
        )

        sponsor = self.get_cell_text(page, "Author")
        bill.add_sponsorship(
            sponsor, classification="primary", entity_type="person", primary=True
        )

        version = self.get_cell(page, "Number").xpath("a/@href")[0]
        bill.add_version_link(bill_id, version, media_type="application/pdf")

        bill.add_source(url)

        bill = self.do_action(bill, page, "Date Introduced", chamber, "introduction")
        bill = self.do_action(bill, page, "House First Reading", "lower", "reading-1")
        bill = self.do_action(bill, page, "House Final Reading", "lower", "reading-2")
        bill = self.do_action(bill, page, "Senate First Reading", "upper", "reading-1")
        bill = self.do_action(bill, page, "Senate Final Reading", "upper", "reading-2")

        last_action = self.get_cell_text(page, "Last Action").strip()
        last_updated = self.get_cell_text(page, "Last Updated")

        if "withdrawn" in last_action.lower():
            bill.add_action(
                "Withdrawn",
                dateutil.parser.parse(last_updated).strftime("%Y-%m-%d"),
                chamber=("upper" if "senate" in last_action.lower() else "lower"),
                classification="withdrawal",
            )

        reports = page.xpath("//a[contains(@url, 'COMMITTEE%20REPORTS')]")
        for report in reports:
            bill.add_document_link(
                report.xpath("text()")[0],
                report.xpath("@url"),
                media_type="application/pdf",
            )

        if last_action != "":
            if self.get_cell_text(
                page, "Senate Committee"
            ) == last_action or self.get_cell_text(
                page, "Senate Committee"
            ) == last_action.replace(
                "SENATE-", ""
            ):
                bill.add_action(
                    last_action,
                    dateutil.parser.parse(last_updated).strftime("%Y-%m-%d"),
                    chamber="upper",
                    classification="referral-committee",
                )

            #  e.g. if "JGO" is house com, and "House-JGO" is last action
            if self.get_cell_text(
                page, "House Committee"
            ) == last_action or self.get_cell_text(
                page, "House Committee"
            ) == last_action.replace(
                "HOUSE-", ""
            ):
                bill.add_action(
                    last_action,
                    dateutil.parser.parse(last_updated).strftime("%Y-%m-%d"),
                    chamber="lower",
                    classification="referral-committee",
                )

        if "duly adopted" in last_action.lower():
            bill.add_action(
                "Duly Adopted",
                dateutil.parser.parse(last_updated).strftime("%Y-%m-%d"),
                chamber="executive",
                classification="enrolled",
            )

        refs = self.get_cell_text(page, "References")
        for line in refs.split("\n"):
            if "governor" in line.lower() or re.match(r"g-\s?\d+", line.lower()):
                action_date = re.findall(r"\d+\/\d+\/\d+", line)[0]
                bill.add_action(
                    "Sent to Governor",
                    dateutil.parser.parse(action_date).strftime("%Y-%m-%d"),
                    chamber="executive",
                    classification="executive-receipt",
                )

        # Public Law, or various local laws
        if "p.l." in last_action.lower() or ".l.l." in last_action.lower():
            bill.add_action(
                last_action,
                dateutil.parser.parse(last_updated).strftime("%Y-%m-%d"),
                chamber="executive",
                classification="became-law",
            )

            if self.get_cell(page, "Last Action").xpath("p/a/@href"):
                bill.add_version_link(
                    last_action,
                    self.get_cell(page, "Last Action").xpath("p/a/@href")[0],
                    media_type="application/pdf",
                )

            if "p.l." in last_action.lower():
                bill.add_citation(
                    "MP Public Laws", last_action, citation_type="chapter"
                )

        yield bill

    # get the table td where the sibling th contains the text
    def get_cell(self, page, text: str):
        return page.xpath(f"//tr[th[contains(text(), '{text}')]]/td")[0]

    def get_cell_text(self, page, text: str) -> str:
        return page.xpath(f"string(//tr[th[contains(text(), '{text}')]]/td)").strip()

    def do_action(self, bill, page, text, chamber, classification):
        action_text = self.get_cell_text(page, text)
        if action_text:

            try:
                action_date = re.findall(r"\d+\/\d+\/\d+", action_text)[0]
            except IndexError:
                if re.match(r"\d+:\d+:\d+ AM", action_text):
                    action_date = self.get_cell_text(page, "Last Updated")
                else:
                    return bill

            bill.add_action(
                text,
                dateutil.parser.parse(action_date).strftime("%Y-%m-%d"),
                chamber=chamber,
                classification=classification,
            )
        return bill
