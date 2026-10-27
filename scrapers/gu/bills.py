import lxml.html
import re

from openstates.scrape import Scraper, Bill


class GUBillScraper(Scraper):
    bill_prefixes = {
        "bill": "B",
        "resolution": "R",
    }

    def scrape(self, session):
        url = "https://guamlegislature.gov/bills/"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath(
            "//a[contains(@href, 'https://guamlegislature.gov/bills-page')]/@href"
        ):
            yield from self.scrape_type(session, link, "bill")

    def scrape_type(self, session, url, billtype):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.cssselect("div.wp-block-column-is-layout-flow p"):
            actions = row.xpath("following-sibling::figure")[0]
            yield from self.scrape_bill(url, session, billtype, row, actions)

    def scrape_bill(self, url, session, billtype, body, actions):
        bill_id = body.xpath(".//strong")[0].text_content()
        bill_id = self.extract_bill_number(bill_id)
        bill_id = f"{self.bill_prefixes[billtype]} {bill_id}"

        title = body.xpath(".//a")[1].text_content()
        # sometimes they put AN  ACT or AN   ACT
        title = re.sub(r"AN\s+ACT", "AN ACT", title)
        if "an act" not in title.lower():
            self.info(f"Unclear markup for {bill_id}, extracting title by regex.")
            # if the title isn't in the initial link, the markup seems to be all over the place.
            title = self.extract_title(body.text_content())

        bill = Bill(
            bill_id, session, title, chamber="legislature", classification=billtype
        )

        for row in body.xpath(
            ".//strong[contains(text(), 'Sponsor')]/following-sibling::a"
        ):
            name = row.text_content().strip()
            if name == "":
                continue
            bill.add_sponsorship(name, "primary", "person", True, chamber="legislature")

        if body.xpath(".//strong[contains(text(), 'Co-Sponsor')]"):
            names = body.xpath(
                ".//strong[contains(text(), 'Co-Sponsor')]/following-sibling::text()[1]"
            )
            if names:
                for name in names[0].split("/"):
                    name = name.strip()
                    if name == "":
                        continue
                    bill.add_sponsorship(
                        name, "cosponsor", "person", False, chamber="legislature"
                    )

        for row in body.xpath(
            ".//a[contains(@href, '.pdf') and (contains(@href, 'History') or contains(@href, 'Res'))]"
        ):
            v_url = row.xpath("@href")[0]
            v_title = row.text_content().strip()
            bill.add_version_link(
                v_title, v_url, media_type="application/pdf", on_duplicate="ignore"
            )

        bill.add_source(url)
        yield bill

    def extract_bill_number(self, bill_id: str) -> str:
        matches = re.findall(r"(\d+-\d+)", bill_id)
        return matches[0]

    def extract_title(self, content: str) -> str:
        # if the title isn't linked, the markup will be a mess of random elements.
        # try to pull it via regex
        matches = re.findall(r"(AN ACT.*)Sponsor:", content)
        return matches[0]
