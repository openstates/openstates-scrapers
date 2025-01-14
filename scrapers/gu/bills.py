# import dateutil
import lxml.html
import pytz
import re

# import tempfile
import html

from openstates.scrape import Scraper, Bill

# from openstates.utils import convert_pdf
# from scrapelib import HTTPError


class GUBillScraper(Scraper):
    _tz = pytz.timezone("Pacific/Guam")

    def scrape(self):
        # bill and res listing pages have different html
        yield from self.scrape_bills("https://guamlegislature.gov/bills/")
        yield from self.scrape_resolutions("https://guamlegislature.gov/resolutions/")

    def scrape_bills(self, url: str):
        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.cssselect("table.has-fixed-layout tr"):
            bill_num_long = row.xpath("td[1]")[0].text_content()
            matches = re.findall(r"(\d+)-(\d+)", bill_num_long, re.IGNORECASE)
            bill_num = matches[0][0]
            session = matches[0][1]

            if "bill" in bill_num_long.lower():
                identifier = f"B {bill_num}"
                classification = "bill"
            elif "resolution" in bill_num_long.lower():
                identifier = f"R {bill_num}"
                classification = "resolution"
            else:
                self.error("Unknown legislation type for {bill_num_long}")
                return

            title = row.xpath("td[1]")[0].text_content()

            bill = Bill(
                identifier,
                session,
                title,
                chamber="legislature",
                classification=classification,
            )

            bill.add_source(url)

            # unescape td[3] then split it by <br>
            sponsors = lxml.html.tostring(row.xpath("td[3]")[0]).decode("utf-8")
            sponsors = sponsors.replace("<td>", "").replace("</td>", "")
            sponsors = html.unescape(sponsors)
            for sponsor in sponsors.split("<br>"):
                bill.add_sponsorship(sponsor, "primary", "person", primary=True)

            if row.xpath("td[2]/a"):
                bill.add_version_link(
                    "Bill Text",
                    row.xpath("td[2]/a/@href")[0],
                    media_type="application/pdf",
                )
            yield bill

    def scrape_resolutions(self, url: str):
        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.xpath("//p[a/strong[contains(text(), 'Resolution No.')]]"):
            bill_num_long = row.xpath("a/strong")[0].text_content()
            matches = re.findall(r"(\d+)-(\d+)", bill_num_long, re.IGNORECASE)
            bill_num = matches[0][0]
            session = matches[0][1]

            if "bill" in bill_num_long.lower():
                identifier = f"B {bill_num}"
                classification = "bill"
            elif "resolution" in bill_num_long.lower():
                identifier = f"R {bill_num}"
                classification = "resolution"
            else:
                self.error("Unknown legislation type for {bill_num_long}")
                return

            title = row.xpath("following-sibling::p[2]")[0].text_content()

            bill = Bill(
                identifier,
                session,
                title,
                chamber="legislature",
                classification=classification,
            )

            bill.add_source(url)

            # unescape td[3] then split it by <br>
            sponsors = row.xpath("following-sibling::p[1]")[0].text_content()
            sponsor = sponsors.split("–")[1].strip()
            bill.add_sponsorship(sponsor, "primary", "organization", primary=True)

            if row.xpath("a"):
                bill.add_version_link(
                    "Resolution Text",
                    row.xpath("a/@href")[0].replace("http:", "https:"),
                    media_type="application/pdf",
                )
            yield bill
