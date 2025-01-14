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

    def scrape_listing(self, url: str):
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

            sponsors = lxml.html.tostring(row.xpath("td[3]")[0]).decode("utf-8")

            sponsors = sponsors.replace("<td>", "").replace("</td>", "")
            sponsors = html.unescape(sponsors)
            for sponsor in sponsors.split("<br>"):
                bill.add_sponsorship(sponsor, "primary", "person", primary=True)

            print(sponsors)
            print(identifier, session)
            yield bill

    def scrape(self):
        yield self.scrape_listing("https://guamlegislature.gov/bills/")

        # # resolutions are at a separate address
        # res_url = f"https://guamlegislature.gov/resolutions/"
        # doc = self.get(res_url).text.split("-->")[-2]
        # for resolution in self.res_match_re.findall(doc):
        #     yield self._process_resolution(session, resolution, res_url)
