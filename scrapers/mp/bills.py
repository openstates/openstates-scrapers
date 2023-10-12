import cloudscraper
import dateutil
import lxml.html
import pytz

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
        "Senate Legislative initiatives:": "LI",
        "Senate Joint Resolutions:": "SJR",
        "Senate Local Bills:": "SLB",
        "Senate Commemorative Resolutions:": "SR",
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

        bill = Bill(
            identifier=bill_id,
            title=title,
            legislative_session=session,
            chamber=chamber,
        )

        sponsor = self.get_cell_text(page, "Author")
        bill.add_sponsorship(
            sponsor, classification="primary", entity_type="person", primary=True
        )

        version = self.get_cell(page, "Number").xpath("a/@href")[0]

        last_action = self.get_cell_text(page, "Last Action")
        bill.add_version_link(last_action, version, media_type="application/pdf")

        bill.add_source(url)

        action_text = self.get_cell_text(page, "Date Introduced")
        if action_text:
            bill.add_action(
                "Introduced",
                dateutil.parser.parse(action_text).strftime("%Y-%m-%d"),
                chamber=chamber,
                classification="introduction",
            )

        yield bill

    # get the table td where the sibling th contains the text
    def get_cell(self, page, text: str):
        return page.xpath(f"//tr[th[contains(text(), '{text}')]]/td")[0]

    def get_cell_text(self, page, text: str) -> str:
        return page.xpath(f"string(//tr[th[contains(text(), '{text}')]]/td)").strip()
