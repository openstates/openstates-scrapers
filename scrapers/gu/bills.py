import dateutil
import lxml.html
import pytz
import re
import tempfile

from openstates.scrape import Scraper, Bill
from openstates.utils import convert_pdf
from scrapelib import HTTPError


class GUBillScraper(Scraper):
    _tz = pytz.timezone("Pacific/Guam")
    # non-greedy match on bills in the "list" page
    bill_match_re = re.compile("(<p>.*?<br>)", re.DOTALL)
    res_match_re = re.compile('(<p align="left">.*?<br>)', re.DOTALL)
    sponsors_match_re = re.compile(r"Sponsor\(s\) -(.*)<p", re.DOTALL)
    desc_match_re = re.compile(r"^\s?<p>(.*?)<li>", re.DOTALL)
    res_desc_match_re = re.compile('<p align="left">([^<>]+)')
    filtered_details = ["BILL HISTORY", "Bill HISTORY", "CLERKS OFFICE", "Page 1"]
    date_re = re.compile("([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})")
    date_time_re = re.compile(
        r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}\s?\n?[0-9]{1,2}:[0-9]{2}\s[apAP]\.?[mM]\.?)",
    )
    committee_re = re.compile("([cC]ommittee on [a-zA-Z, \n]+)")

    bill_prefixes = {
        "bill": "B",
        "resolution": "R",
    }

    def _download_pdf(self, url: str):
        try:
            res = self.get(url)
        except HTTPError:
            # This vote document wasn't found.
            msg = "No document found at url %r" % url
            self.logger.warning(msg)
            return
        fd = tempfile.NamedTemporaryFile()
        fd.write(res.content)
        text = convert_pdf(fd.name, type="xml")
        data = lxml.html.fromstring(text).xpath("//text")
        # filter out empty and obvious text we don't need
        return "\n".join(
            [
                d.text
                for d in data
                if d.text
                and d.text.strip()
                and d.text.strip() not in self.filtered_details
            ]
        )

    def _get_bill_details(self, url: str):
        text_only = self._download_pdf(url)
        if not text_only:
            return {}
        details = {"IntroducedDate": None, "ReferredDate": None, "Committee": None}
        full_dates = self.date_time_re.findall(text_only)
        days = self.date_re.findall(text_only)
        if full_dates:
            details["IntroducedDate"] = self._tz.localize(
                dateutil.parser.parse(full_dates[1])
            )
        if len(days) > 2:
            details["ReferredDate"] = self._tz.localize(dateutil.parser.parse(days[2]))
        committee = self.committee_re.search(text_only)
        if committee:
            details["Committee"] = " ".join(
                committee.group(1).replace("\n", " ").split()
            )
        return details

    def _get_resolution_details(self, url: str):
        text_only = self._download_pdf(url)
        if not text_only:
            return {}
        details = {
            "IntroducedDate": None,
            "PresentationDate": None,
        }
        full_dates = self.date_time_re.findall(text_only)
        if full_dates:
            details["IntroducedDate"] = self._tz.localize(
                dateutil.parser.parse(full_dates[0])
            )
            if len(full_dates) > 1:
                details["PresentationDate"] = self._tz.localize(
                    dateutil.parser.parse(full_dates[1])
                )
        return details

    def _process_bill(self, session: str, bill: str, root_url: str):
        xml = lxml.html.fromstring(bill)
        xml.make_links_absolute(root_url)
        # Bill No. 163-37 (LS) or Bill No. 160-37 (LS) - WITHDRAWN match
        name_parts = (
            xml.xpath("//strong")[0].text.strip().removeprefix("Bill No. ").split()
        )
        name = f'B-{name_parts[0].strip().removeprefix("Bill No. ")}'
        # bill_type = name_parts[1].strip("(").strip(")")
        bill_link = xml.xpath("//a/@href")[0]
        bill_obj = Bill(
            name,
            legislative_session=session,
            title="See Introduced Link",
            classification="bill",
        )
        bill_obj.add_source(root_url, note="Bill Index")
        # withdrawn bills don't have regular links, so we dig elsewhere
        if "WITHDRAWN" in "".join(name_parts):
            bill_obj.add_source(url=bill_link, note="Bill Introduced")
            details = self._get_bill_details(bill_link)
            if details.get("IntroducedDate", None):
                bill_obj.add_action(
                    "Introduced", details["IntroducedDate"], chamber="legislature"
                )
            if details.get("ReferredDate", None):
                if details["Committee"]:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        chamber="legislature",
                    )
                else:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        chamber="legislature",
                    )

            yield bill_obj
        else:
            bill_obj.add_version_link(
                url=bill_link, note="Bill Introduced", media_type="application/pdf"
            )
            status = xml.xpath("//li")[0].xpath("a/@href")[0]
            bill_obj.add_source(url=status, note="Bill Status")
            description = (
                self.desc_match_re.search(bill).group(1).strip().split("<p>")[-1]
            )
            if description:
                bill_obj.title = description.title()
            # sponsors are deliniated by / and \n, so we need to strip many characters
            sponsors = [
                s.strip("/").strip()
                for s in self.sponsors_match_re.search(bill).group(1).split("\n")
                if s.strip()
            ]
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

            for link in xml.xpath("//li")[1:]:
                url = link.xpath("a/@href")[0]
                title = link.xpath("a")[0].text
                if "fiscal note" in title.lower():
                    bill_obj.add_document_link(
                        url=url,
                        note=title,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )
                else:
                    bill_obj.add_version_link(
                        url=url,
                        note=title,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

            # status PDF has introduced/passed/etc. dates
            details = self._get_bill_details(status)
            if details.get("IntroducedDate", None):
                bill_obj.add_action(
                    "Introduced", details["IntroducedDate"], chamber="legislature"
                )
            if details.get("ReferredDate", None):
                if details["Committee"]:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        chamber="legislature",
                    )
                else:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        chamber="legislature",
                    )
            yield bill_obj

    def _process_resolution(self, session: str, bill: str, root_url: str):
        xml = lxml.html.fromstring(bill)
        xml.make_links_absolute(root_url)
        res_parts = xml.xpath("//a")[0].text.removeprefix("Resolution No. ").split()
        name = f"R-{res_parts[0].strip()}"
        # res_type = res_parts[1].strip(")").strip("(")
        bill_link = xml.xpath("//a/@href")[0]
        bill_obj = Bill(
            name,
            legislative_session=session,
            title="See Resolution Introduced Link",
            classification="resolution",
        )
        if not self.res_desc_match_re.search(bill):
            self.warning(f"Skipping resolution {bill}")
            return
        description = self.res_desc_match_re.search(bill).group(1).strip()

        if len(description) > 0:
            bill_obj.title = description
        bill_obj.add_source(root_url, note="Resolution Index")
        bill_obj.add_source(bill_link, note="Resolution Introduced")
        # sponsors are deliniated by / and \n, so we need to strip many characters
        sponsors = [
            s.strip("/").strip().removesuffix("</p>")
            for s in self.sponsors_match_re.search(bill).group(1).split("\n")
            if s.strip()
        ]
        # clean up steps may empty out a value by accident, so remove empty objects again
        sponsors = [s for s in sponsors if s]
        result = None
        result_date = None

        if "-" in sponsors[-1]:
            name, result_data = sponsors[-1].split("-")
            sponsors[-1] = name
            result_data = result_data.split()
            result = result_data[0]
            if len(result_data) > 1:
                result_date = self._tz.localize(dateutil.parser.parse(result_data[1]))

        if result and result_date:
            bill_obj.add_action(result, result_date, chamber="legislature")

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
        for link in xml.xpath("//li"):
            url = link.xpath("a/@href")[0]
            title = link.xpath("a")[0].text
            if "fiscal note" in title.lower():
                bill_obj.add_document_link(
                    url=url,
                    note=title,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )
            else:
                bill_obj.add_version_link(
                    url=url,
                    note=title,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

        bill_obj.add_version_link(
            url=bill_link, note="Current Status", media_type="application/pdf"
        )

        details = self._get_resolution_details(bill_link)
        if details.get("IntroducedDate", None):
            bill_obj.add_action(
                "Introduced", details["IntroducedDate"], chamber="legislature"
            )
        if details.get("PresentationDate", None):
            bill_obj.add_action(
                "Presented", details["PresentationDate"], chamber="legislature"
            )
        yield bill_obj

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
