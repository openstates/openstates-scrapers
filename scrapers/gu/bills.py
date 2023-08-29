import re
import lxml.html
from lxml.etree import tostring
import tempfile

from openstates.scrape import Scraper, Bill
from openstates.utils import convert_pdf


class GUBillScraper(Scraper):
    bill_match_re = re.compile("(<p>.*?<br>)", re.DOTALL)
    sponsors_match_re = re.compile(r"Sponsor\(s\) -(.*)<p>", re.DOTALL)
    desc_match_re = re.compile(r"^\s?<p>(.*?)<li>", re.DOTALL)
    withdrawn_re = re.compile("WITHDRAWN", re.DOTALL)

    def _download_pdf(self, url: str):
        res = self.get(url)
        fd = tempfile.NamedTemporaryFile()
        fd.write(res.content)
        text = convert_pdf(fd.name, type="xml")
        fd.close()
        if not text.strip():
            raise Exception(f"{url} produced empty PDF")
        return lxml.html.fromstring(text)

    def scrape(self, session):
        bills_url = f"https://guamlegislature.com/{session}_Guam_Legislature/{session}_bills_intro_content.htm"
        doc = self.get(bills_url).text.split("-->")[-1]
        for bill in self.bill_match_re.findall(doc):
            if self.withdrawn_re.search(bill):
                continue
            sponsors = [
                s.strip("/").strip()
                for s in self.sponsors_match_re.search(bill).group(1).split("\n")
                if s.strip()
            ]
            description = self.desc_match_re.search(bill).group(1).strip()
            xml = lxml.html.fromstring(bill)
            xml.make_links_absolute(bills_url)
            name = xml.xpath("//strong")[0].text.strip()
            status = xml.xpath("//li")[0].xpath("a/@href")[0]

            bill_obj = Bill(
                name,
                legislative_session=session,
                chamber="unicameral",
                title=description.title(),
            )

            bill_obj.add_sponsorship(
                name=sponsors[0],
                entity_type="person",
                classification="primary",
                primary=True,
            )
            for sponsor in sponsors[1:]:
                bill_obj.add_sponsorship(
                    name=sponsor,
                    entity_type="person",
                    classification="cosponsor",
                    primary=False,
                )

            bill_obj.add_source(bills_url, note="Bill Index")
            bill_obj.add_document_link(url=status, note="Bill Status")
            for link in xml.xpath("//li")[1:]:
                url = link.xpath("a/@href")[0]
                title = link.xpath("a")[0].text
                bill_obj.add_document_link(url=url, note=title)

            details = self._download_pdf(status)
            print(tostring(details, pretty_print=True))
            exit(1)
            yield bill_obj
