import datetime
import lxml
import pytz
import re
import scrapelib
import xml.etree.ElementTree as ET

from openstates.scrape import Bill, Scraper

# NOTE: This is a US federal bill scraper designed to output bills in the
# openstates format, for compatibility with systems that already ingest the pupa format.

# If you're looking to just collect federal bill data, you're probably better off with
# https://github.com/unitedstates/congress which offers more backdata.


class USBillScraper(Scraper):
    # https://www.govinfo.gov/rss/billstatus-batch.xml
    # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md

    # good sample bills:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
    # vetoed:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml

    # custom namespace, see
    # https://docs.python.org/2/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
    ns = {"us": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    _TZ = pytz.timezone("US/Eastern")

    chambers = {"House": "lower", "Joint": "joint", "Senate": "upper"}
    chamber_map = {"upper": "s", "lower": "h"}

    classifications = {
        "HRES": "resolution",
        "HCONRES": "resolution",
        "HR": "bill",
        "HJRES": "resolution",
        "SRES": "resolution",
        "SJRES": "resolution",
        "S": "bill",
        "SCONRES": "resolution",
    }

    # to scrape everything UPDATED after a given date/time, start="2020-01-01 22:01:01"
    def scrape(self, chamber=None, session=None, start=None):
        if start:
            start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%I:%S")
        else:
            start = datetime.datetime(1980, 1, 1, 0, 0, 1)

        sitemap_url = (
            "https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS/sitemapindex.xml"
        )
        sitemaps = self.get(sitemap_url).content
        root = ET.fromstring(sitemaps)

        # if you want to test a bill:
        # yield from self.parse_bill('https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr3884.xml')

        for link in root.findall("us:sitemap/us:loc", self.ns):
            # split by /, then check that "116s" matches the chamber
            if chamber:
                link_parts = link.text.split("/")
                chamber_code = link_parts[-2][3]
                if chamber_code != self.chamber_map[chamber]:
                    continue

            if session in link.text:
                yield from self.parse_bill_list(link.text, start)

    def parse_bill_list(self, url, start):
        sitemap = self.get(url).content
        root = ET.fromstring(sitemap)
        for row in root.findall("us:url", self.ns):
            date = datetime.datetime.fromisoformat(
                self.get_xpath(row, "us:lastmod")[:-1]
            )

            if date > start:
                self.info(
                    "{} > {}, scraping".format(
                        datetime.datetime.strftime(date, "%c"),
                        datetime.datetime.strftime(start, "%c"),
                    )
                )
                bill_url = self.get_xpath(row, "us:loc")
                yield from self.parse_bill(bill_url)

    def parse_bill(self, url):
        xml = self.get(url).content
        xml = ET.fromstring(xml)

        bill_num = self.get_xpath(xml, "bill/billNumber")
        bill_type = self.get_xpath(xml, "bill/billType")

        bill_id = "{} {}".format(bill_type, bill_num)

        chamber_name = self.get_xpath(xml, "bill/originChamber")
        chamber = self.chambers[chamber_name]

        title = self.get_xpath(xml, "bill/title")

        classification = self.classifications[bill_type]

        session = self.get_xpath(xml, "bill/congress")

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=classification,
        )

        self.scrape_actions(bill, xml)
        self.scrape_amendments(bill, xml, session, chamber, bill_id)
        self.scrape_cbo(bill, xml)
        self.scrape_committee_reports(bill, xml)
        self.scrape_cosponsors(bill, xml)
        self.scrape_laws(bill, xml)
        self.scrape_related_bills(bill, xml)
        self.scrape_sponsors(bill, xml)
        self.scrape_subjects(bill, xml)
        self.scrape_summaries(bill, xml)
        self.scrape_titles(bill, xml)
        self.scrape_versions(bill, xml)

        xml_url = "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{type}/BILLSTATUS-{congress}{type}{num}.xml"
        bill.add_source(
            xml_url.format(congress=session, type=bill_type.lower(), num=bill_num)
        )
        # need to get Congress.gov URL for source & additional versions
        # https://www.congress.gov/bill/116th-congress/house-bill/1
        cg_url = (
            "https://congress.gov/bill/{congress}th-congress/{chamber}-{type}/{num}"
        )
        cg_url = cg_url.format(
            congress=session,
            chamber=chamber_name.lower(),
            type=classification.lower(),
            num=bill_num,
        )
        bill.add_source(cg_url)

        # use cg_url to get additional version for public law
        # disabled 9/2021 - congress.gov was giving 503s
        # self.scrape_public_law_version(bill, cg_url)

        yield bill

    def build_sponsor_name(self, row):
        first_name = self.get_xpath(row, "firstName")
        middle_name = self.get_xpath(row, "middleName")
        last_name = self.get_xpath(row, "lastName")
        return " ".join(filter(None, [first_name, middle_name, last_name]))

    # LOC actions don't make the chamber clear, but you can deduce it from the codes
    # https://github.com/usgpo/bill-status/blob/main/BILLSTATUS-XML_User_User-Guide.md
    def classify_actor_by_code(self, action_code: str):
        if action_code is None:
            return False

        if action_code[0:1] == "H":
            return "lower"
        elif action_code[0:1] == "E":
            return "executive"

        if action_code.isdigit():
            code = int(action_code)
            if code < 10000:
                return "lower"
            elif code < 28000:
                return "upper"
            else:
                return "executive"

        return False

    def classify_action_by_code(self, action):
        if action is None:
            return None
        # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md
        # see table 3, Action Code Element Possible Values

        # https://github.com/openstates/openstates-core/blob/082210489693b31e6534bd8328bfb895427e9eed/openstates/data/common.py
        # for the OS codes
        codes = {
            # note: E3000 can also mean vetoed, so catch executive signatures by the action text
            # see https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml
            # 'E30000': 'executive-signature',
            "31000": "executive-veto",
            "E20000": "executive-receipt",
            "E40000": "became-law",
            "H11100": "referral-committee",
            "H11200": "referral-committee",
            "H14000": "receipt",
            "1000": "introduction",
            "2000": "referral-committee",
            "8000": "passage",
            "10000": "introduction",
            "11000": "referral-committee",
            "14000": "referral",
            "17000": "passage",
            "28000": "executive-receipt",
            "36000": "became-law",
            # TODO: is this always passage or do we have to check the result?
            # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
            "H37300": "passage",
            "Intro-H": "introduction",
        }

        return codes.get(action)

    def classify_action_by_name(self, action):
        action_classifiers = [
            ("Read the second time", ["reading-2"]),
            (
                "Received in the Senate. Read the first time",
                ["introduction", "reading-1"],
            ),
            ("Signed by President", ["executive-signature"]),
            ("Vetoed by President", ["executive-veto"]),
            ("Failed of passage in Senate over veto by", ["veto-override-failure"]),
        ]
        for regex, classification in action_classifiers:
            if re.match(regex, action):
                return classification
        return None

    def get_xpath(self, xml, xpath):
        if not xml.findall(xpath, self.ns):
            return
        return xml.findall(xpath, self.ns)[0].text

    def scrape_actions(self, bill, xml):
        # TODO: Skip all LOC actions? just some LOC actions?

        # list for deduping
        actions = []
        for row in xml.findall("bill/actions/item"):
            action_text = self.get_xpath(row, "text")
            if action_text not in actions:
                source = self.get_xpath(row, "sourceSystem/name")
                action_type = self.get_xpath(row, "type")

                actor = "lower"
                if "Senate" in source:
                    actor = "upper"
                elif "House" in source:
                    actor = "lower"
                elif action_type == "BecameLaw" or action_type == "President":
                    actor = "executive"

                # LOC doesn't make the actor clear, but you can back into it
                # from the actions
                if source == "Library of Congress":
                    possible_actor = self.classify_actor_by_code(
                        self.get_xpath(row, "actionCode")
                    )
                    if possible_actor is not None:
                        actor = possible_actor

                # house actions give a time, senate just a date
                if row.findall("actionTime"):
                    action_date = "{} {}".format(
                        self.get_xpath(row, "actionDate"),
                        self.get_xpath(row, "actionTime"),
                    )
                    action_date = datetime.datetime.strptime(
                        action_date, "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    action_date = datetime.datetime.strptime(
                        self.get_xpath(row, "actionDate"), "%Y-%m-%d"
                    )
                action_date = self._TZ.localize(action_date)

                classification = self.classify_action_by_code(
                    self.get_xpath(row, "actionCode")
                )

                # senate actions dont have a code
                if classification is None:
                    classification = self.classify_action_by_name(action_text)

                bill.add_action(
                    action_text,
                    action_date,
                    chamber=actor,
                    classification=classification,
                )
                actions.append(action_text)

    def scrape_amendments(self, bill, xml, session, chamber, bill_id):
        slugs = {
            "HAMDT": "house-amendment",
            "SAMDT": "senate-amendment",
        }
        amdt_url = (
            "https://www.congress.gov/amendment/{session}th-congress/{slug}/{num}"
        )
        amdt_name = "{type} {num}"

        for row in xml.findall("bill/amendments/amendment"):
            session = self.get_xpath(row, "congress")
            num = self.get_xpath(row, "number")

            # 201st not 200th. If congress.gov's url scheme survivess 10 years,
            # I apologize, future maintainer.
            if int(session) > 200:
                self.warning("Check amendment url ordinals")

            bill.add_document_link(
                note=amdt_name.format(
                    type=self.get_xpath(row, "type"),
                    num=num,
                ),
                url=amdt_url.format(
                    session=session, slug=slugs[self.get_xpath(row, "type")], num=num
                ),
                media_type="text/html",
            )

        # ex: https://rules.house.gov/bill/116/hr-3884
        if chamber == "lower":
            rules_url = "https://rules.house.gov/bill/{}/{}".format(
                session, bill_id.replace(" ", "-")
            )
            try:
                page = lxml.html.fromstring(self.get(rules_url).content)
                page.make_links_absolute(rules_url)
                for row in page.xpath(
                    '//article[contains(@class, "field-name-field-amendment-table")]/div/div/table/tr'
                ):
                    if row.xpath("td[3]/a"):
                        amdt_num = row.xpath("td[1]/text()")[0].strip()
                        amdt_sponsor = row.xpath("td[3]/a/text()")[0].strip()
                        amdt_name = "House Rules Committee Amendment {} - {}".format(
                            amdt_num, amdt_sponsor
                        )
                        self.info(amdt_name)
                        amdt_url = row.xpath("td[3]/a/@href")[0].strip()
                        if not amdt_url.startswith("http"):
                            continue
                        bill.add_document_link(
                            note=amdt_name,
                            url=amdt_url,
                            media_type="application/pdf",
                        )
            except scrapelib.HTTPError:
                # Not every bill has a rules committee page
                return

    # CBO cost estimates
    def scrape_cbo(self, bill, xml):
        for row in xml.findall("bill/cboCostEstimates/item"):
            bill.add_document_link(
                note="CBO: {}".format(self.get_xpath(row, "title")),
                url=self.get_xpath(row, "url"),
                media_type="text/html",
            )

    # ex: https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr1218.xml
    def scrape_committee_reports(self, bill, xml):
        crpt_url = "https://www.congress.gov/{session}/crpt/{chamber}rpt{num}/CRPT-{session}{chamber}rpt{num}.pdf"
        regex = r"(?P<chamber>[H|S|J])\.\s+Rept\.\s+(?P<session>\d+)-(?P<num>\d+)"

        for row in xml.findall("bill/committeeReports/committeeReport"):
            report = self.get_xpath(row, "citation")
            match = re.search(regex, report)

            url = crpt_url.format(
                session=match.group("session"),
                chamber=match.group("chamber").lower(),
                num=match.group("num"),
            )

            bill.add_document_link(note=report, url=url, media_type="application/pdf")

    def scrape_cosponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall("bill/cosponsors/item"):
            if not self.get_xpath(row, "sponsorshipWithdrawnDate"):
                bill.add_sponsorship(
                    self.build_sponsor_name(row),
                    classification="cosponsor",
                    primary=False,
                    entity_type="person",
                )
                all_sponsors.append(self.get_xpath(row, "bioguideId"))
        bill.extras["cosponsor_bioguides"] = all_sponsors

    def scrape_laws(self, bill, xml):
        # ex. public law, https://www.govinfo.gov/bulkdata/BILLSTATUS/117/s/BILLSTATUS-117s325.xml
        # ex. private law, https://www.govinfo.gov/bulkdata/BILLSTATUS/115/hr/BILLSTATUS-115hr4641.xml

        for row in xml.findall("bill/laws/item"):
            law_type = self.get_xpath(row, "type")
            law_ref = self.get_xpath(row, "number")

            url_slug = "pvtl" if law_type == "Private Law" else "publ"

            law_url_pattern = "https://www.congress.gov/{congress}/plaws/{url_slug}{num}/PLAW-{congress}{url_slug}{num}.pdf"

            congress, plaw = law_ref.split("-")
            law_url = law_url_pattern.format(
                congress=congress, num=plaw, url_slug=url_slug
            )

            bill.add_citation(
                f"US {law_type}", law_ref, citation_type="final", url=law_url
            )

    def scrape_related_bills(self, bill, xml):
        for row in xml.findall("bill/relatedBills/item"):
            identifier = "{type} {num}".format(
                type=self.get_xpath(row, "type"), num=self.get_xpath(row, "number")
            )

            bill.add_related_bill(
                identifier=identifier,
                legislative_session=self.get_xpath(row, "congress"),
                relation_type="companion",
            )

    def scrape_sponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall("bill/sponsors/item"):
            if not row.findall("sponsorshipWithdrawnDate"):
                bill.add_sponsorship(
                    self.build_sponsor_name(row),
                    classification="primary",
                    primary=True,
                    entity_type="person",
                )
                all_sponsors.append(self.get_xpath(row, "bioguideId"))
        bill.extras["sponsor_bioguides"] = all_sponsors

    def scrape_subjects(self, bill, xml):
        for row in xml.findall("bill/subjects/billSubjects/legislativeSubjects/item"):
            bill.add_subject(self.get_xpath(row, "name"))

    def scrape_summaries(self, bill, xml):
        seen_abstracts = set()
        for row in xml.findall("bill/summaries/billSummaries/item"):
            abstract = self.get_xpath(row, "text")

            if abstract not in seen_abstracts:
                bill.add_abstract(
                    abstract=abstract,
                    note=self.get_xpath(row, "name"),
                )
                seen_abstracts.add(abstract)

    def scrape_titles(self, bill, xml):
        all_titles = set()
        # add current title to prevent dupes
        all_titles.add(bill.title)

        for alt_title in xml.findall("bill/titles/item"):
            all_titles.add(self.get_xpath(alt_title, "title"))

        all_titles.remove(bill.title)

        for title in all_titles:
            bill.add_title(title)

    def scrape_versions(self, bill, xml):
        for row in xml.findall("bill/textVersions/item"):
            version_title = self.get_xpath(row, "type")
            try:
                version_date = self.get_xpath(row, "date")[:10]
            except TypeError:
                version_date = ""

            for version in row.findall("formats/item"):
                url = self.get_xpath(version, "url")
                bill.add_version_link(
                    note=version_title,
                    url=url,
                    media_type="text/xml",
                    date=version_date,
                )
                bill.add_version_link(
                    note=version_title,
                    url=url.replace("xml", "pdf"),
                    media_type="application/pdf",
                    date=version_date,
                )

    def scrape_public_law_version(self, bill, url):
        # only try to scrape public law version if there's an enrolled version
        if not any(["Enrolled" in v["note"] for v in bill.versions]):
            return
        # S 164 is timing out so skipping for now
        # https://github.com/openstates/issues/issues/482
        elif bill.title == "Advancing Education on Biosimilars Act of 2021":
            return

        resp = self.get(url + "/text")
        doc = lxml.html.fromstring(resp.content)
        doc.make_links_absolute(url)

        try:
            latest_version = doc.xpath("//select[@id='textVersion']/option/text()")[0]
        except IndexError:
            return
        if "Public Law" in latest_version:
            month, day, year = re.findall(r"(\d{2})/(\d{2})/(\d{4})", latest_version)[0]
            date = f"{year}-{month}-{day}"
            latest_version_url = doc.xpath("//a[text()='PDF']/@href")[0]
            bill.add_version_link(
                note="Public Law",
                url=latest_version_url,
                media_type="application/pdf",
                date=date,
            )
