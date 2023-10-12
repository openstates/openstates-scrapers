import cloudscraper

# import dateutil
import lxml.html
import pytz

from openstates.scrape import Scraper, Bill


class MPBillScraper(Scraper):
    _tz = pytz.timezone("Pacific/Guam")

    scraper = cloudscraper.create_scraper()
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
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
            bill_id = row.xpath("td[1]/text()")[0].strip()
            bill_id = bill_id.replace("\u00a0", " ")
            title = row.xpath("td[3]/text()")[0].strip()

            bill = Bill(
                identifier=bill_id,
                title=title,
                legislative_session=session,
                chamber=chamber,
            )

            bill_url = row.xpath("td[4]/a/@href")[0]
            yield from self.scrape_bill(chamber, bill, bill_url)

    def scrape_bill(self, chamber, bill, url):
        self.info(f"GET {url}")
        page = self.scraper.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        sponsor = self.get_cell_text(page, "Author")
        bill.add_sponsorship(
            sponsor, classification="primary", entity_type="person", primary=True
        )

        version = self.get_cell(page, "Number").xpath("a/@href")[0]

        last_action = self.get_cell_text(page, "Last Action")
        bill.add_version_link(last_action, version, media_type="application/pdf")

        bill.add_source(url)

        yield bill

    # get the table td where the sibling th contains the text
    def get_cell(self, page, text: str):
        return page.xpath(f"//tr[th[contains(text(), '{text}')]]/td")[0]

    def get_cell_text(self, page, text: str) -> str:
        return page.xpath(f"string(//tr[th[contains(text(), '{text}')]]/td)").strip()
