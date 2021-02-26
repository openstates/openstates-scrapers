import re
import datetime
import lxml.html
import requests
from openstates.scrape import Scraper, Bill


class IABillScraper(Scraper):
    def scrape(self, session=None, chamber=None, prefiles=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # openstates/issues#252 - IA continues to prefile after session starts
        # so we'll continue scraping both
        yield from self.scrape_prefiles(session)

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # We need a good bill page to scrape from. Check for "HF " + bill_offset
        bill_offset = "HR1"

        base_url = "https://www.legis.iowa.gov/legislation/BillBook?ga=%s&ba=%s"

        session_id = self.get_session_id(session)
        url = base_url % (session_id, bill_offset)
        page = lxml.html.fromstring(self.get(url).text)

        if chamber == "upper":
            bname = "senateBills"
        else:
            bname = "houseBills"

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()

            if bill_id.lower() == "pick one":
                continue

            bill_url = base_url % (session_id, bill_id)

            yield self.scrape_bill(chamber, session, session_id, bill_id, bill_url)

    # IA does prefiles on a seperate page, with no bill numbers,
    # after introduction they'll link bill numbers to the prefile doc id
    def scrape_prefiles(self, session):
        url = "https://www.legis.iowa.gov/legislation/billTracking/prefiledBills"
        page = lxml.html.fromstring(self.get(url).content)
        page.make_links_absolute(url)

        for row in page.xpath('//table[contains(@class, "sortable")]/tr[td]'):
            title = row.xpath("td[2]/a/text()")[0].strip()
            url = row.xpath("td[2]/a/@href")[0]

            bill_id = self.extract_doc_id(title)

            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber="legislature",
                title=title,
                classification="proposed bill",
            )

            if row.xpath("td[3]/a"):
                document_url = row.xpath("td[3]/a/@href")[0]
                if ".docx" in document_url:
                    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ".pdf" in document_url:
                    media_type = "application/pdf"
                bill.add_document_link(
                    note="Backround Statement", url=document_url, media_type=media_type
                )

            bill.add_version_link(
                note="Prefiled", url=url, media_type="application/pdf"
            )

            bill.add_source(url)

            yield bill

    def extract_doc_id(self, title):
        doc_id = re.findall(r"\((\d{4}\w{2})\)", title)
        return doc_id[0]

    def scrape_subjects(self, bill, bill_number, session, req):

        req.headers.update({"X-Requested-With": "XMLHttpRequest"})

        session_id = self.get_session_id(session)
        bill_id = bill_number.replace(" ", "+")
        subject_url = (
            "https://www.legis.iowa.gov/legislation/BillBook?ga={}"
            "&billName={}&billVersion=i&action=getTaggedTopics&bl=false".format(
                session_id, bill_id
            )
        )

        html = req.get(subject_url, cookies=req.cookies).text
        page = lxml.html.fromstring(html)

        subjects = page.xpath('//div[@class="taggedTopics"]/a/text()')
        for subject in subjects:
            bill.add_subject(subject.strip())

    def scrape_bill(self, chamber, session, session_id, bill_id, url):
        sidebar = lxml.html.fromstring(self.get(url).text)
        sidebar.make_links_absolute("https://www.legis.iowa.gov")

        hist_url = (
            f"https://www.legis.iowa.gov/legislation/billTracking/"
            f"billHistory?billName={bill_id}&ga={session_id}"
        )
        req_session = requests.Session()
        req = requests.get(hist_url)
        if req.status_code == 500:
            self.warning("500 error on {}, skipping".format(hist_url))
            return

        page = lxml.html.fromstring(req.text)
        page.make_links_absolute("https://www.legis.iowa.gov")

        title = page.xpath(
            'string(//div[@id="content"]/div[@class=' '"divideVert"]/div/div[4]/div[2])'
        ).strip()

        if title == "":
            # Sometimes the title is moved, see
            # https://www.legis.iowa.gov/legislation/billTracking/billHistory?billName=SF%20139&ga=88
            title = page.xpath(
                'string(//div[@id="content"]/div[@class=' '"divideVert"]/div[4]/div[2])'
            ).strip()
            if title == "":
                self.warning("URL: %s gives us an *EMPTY* bill. Aborting." % url)
                return

        if title.lower().startswith("in"):
            title = page.xpath("string(//table[2]/tr[3])").strip()

        if "HR" in bill_id or "SR" in bill_id:
            bill_type = ["resolution"]
        elif "HJR" in bill_id or "SJR" in bill_id:
            bill_type = ["joint resolution"]
        elif "HCR" in bill_id or "SCR" in bill_id:
            bill_type = ["concurrent resolution"]
        else:
            bill_type = ["bill"]

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )

        bill.add_source(hist_url)

        # base url for text version (version_abbrev, session_id, bill_id)
        version_html_url_template = (
            "https://www.legis.iowa.gov/docs/"
            "publications/LG{}/{}/attachments/{}.html"
        )
        version_pdf_url_template = (
            "https://www.legis.iowa.gov/docs/" "publications/LG{}/{}/{}.pdf"
        )

        # get pieces of version_link
        vpieces = sidebar.xpath('//select[@id="billVersions"]/option')
        if vpieces:
            for version in vpieces:
                version_name = version.text
                version_abbrev = version.xpath("string(@value)")

                # Get HTML document of bill version.
                version_html_url = version_html_url_template.format(
                    version_abbrev.upper(), session_id, bill_id.replace(" ", "")
                )

                bill.add_version_link(
                    note=version_name, url=version_html_url, media_type="text/html"
                )

                # Get PDF document of bill version.
                version_pdf_url = version_pdf_url_template.format(
                    version_abbrev.upper(), session_id, bill_id.replace(" ", "")
                )

                if "Marked Up" in version_name:
                    version_pdf_url = sidebar.xpath(
                        "//iframe[@id='bbContextDoc']/@src"
                    )[0]

                bill.add_version_link(
                    note=version_name, url=version_pdf_url, media_type="application/pdf"
                )

        sponsors_str = page.xpath(
            'string(//div[@id="content"]/div[@class=' '"divideVert"]/div/div[4]/div[1])'
        ).strip()

        if re.search("^By ", sponsors_str):
            sponsors = re.split(",| and ", sponsors_str.split("By ")[1])
        # for some bills sponsors listed in different format
        else:
            sponsors = re.findall(
                r"[\w-]+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)", sponsors_str
            )

        for sponsor in sponsors:
            sponsor = sponsor.replace(" and", "").strip(" .,")

            # a few sponsors get mangled by our regex
            sponsor = {
                "Means": "Ways & Means",
                "Iowa": "Economic Growth/Rebuild Iowa",
                "Safety": "Public Safety",
                "Resources": "Human Resources",
                "Affairs": "Veterans Affairs",
                "Protection": "Environmental Protection",
                "Government": "State Government",
                "Boef": "De Boef",
            }.get(sponsor, sponsor)

            if sponsor[0].islower():
                # SSBs catch cruft in it ('charges', 'overpayments')
                # https://sunlight.atlassian.net/browse/DATA-286
                continue

            bill.add_sponsorship(
                name=sponsor,
                classification="primary",
                entity_type="person",
                primary=True,
            )

        for tr in page.xpath(
            "//table[contains(@class, 'billActionTable')][1]/tbody/tr"
        ):
            date = tr.xpath("string(td[contains(text(), ', 20')])").strip()
            if date.startswith("***"):
                continue
            elif "No history is recorded at this time." in date:
                return
            if date == "":
                continue

            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[3])").strip()
            action = re.sub(r"\s+", " ", action)

            # Capture any amendment links.
            links = [link for link in [version["links"] for version in bill.versions]]
            version_urls = [link["url"] for link in [i for sub in links for i in sub]]
            if "amendment" in action.lower():
                for anchor in tr.xpath(".//a[1]"):
                    if "-" in anchor.text:
                        # https://www.legis.iowa.gov/docs/publications/AMDI/88/S3071.pdf
                        amd_pattern = "https://www.legis.iowa.gov/docs/publications/AMDI/{}/{}.pdf"
                        amd_id = anchor.text.replace("-", "").strip()
                        amd_url = amd_pattern.format(session_id, amd_id)
                        amd_name = "Amendment {}".format(anchor.text.strip())

                        if amd_url not in version_urls:
                            bill.add_version_link(
                                note=amd_name, url=amd_url, media_type="application/pdf"
                            )
                            version_urls.append(amd_url)
                        else:
                            self.info("Already Added {}, skipping".format(amd_url))

            if "S.J." in action or "SCS" in action:
                actor = "upper"
            elif "H.J." in action or "HCS" in action:
                actor = "lower"
            else:
                actor = "legislature"

            action = re.sub(r"(H|S)\.J\.\s+\d+\.$", "", action).strip()

            if action.startswith("Introduced"):
                atype = ["introduction"]
                if ", referred to" in action:
                    atype.append("referral-committee")
            elif action.startswith("Read first time"):
                atype = "reading-1"
            elif action.startswith("Referred to"):
                atype = "referral-committee"
            elif action.startswith("Sent to Governor"):
                atype = "executive-receipt"
            elif action.startswith("Reported Signed by Governor"):
                atype = "executive-signature"
            elif action.startswith("Signed by Governor"):
                atype = "executive-signature"
            elif action.startswith("Vetoed by Governor"):
                atype = "executive-veto"
            elif action.startswith("Item veto"):
                atype = "executive-veto-line-item"
            elif re.match(r"Passed (House|Senate)", action):
                atype = "passage"
            elif re.match(r"Amendment (S|H)-\d+ filed", action):
                atype = ["amendment-introduction"]
                if ", adopted" in action:
                    atype.append("amendment-passage")
            elif re.match(r"Amendment (S|H)-\d+( as amended,)? adopted", action):
                atype = "amendment-passage"
            elif re.match(r"Amendment (S|N)-\d+ lost", action):
                atype = "amendment-failure"
            elif action.startswith("Resolution filed"):
                atype = "introduction"
            elif action.startswith("Resolution adopted"):
                atype = "passage"
            elif action.startswith("Committee report") and action.endswith("passage."):
                atype = "committee-passage"
            elif action.startswith("Withdrawn"):
                atype = "withdrawal"
            else:
                atype = None

            if action.strip() == "":
                continue

            if re.search(r"END OF \d+ ACTIONS", action):
                continue

            if "$history" not in action:
                bill.add_action(
                    description=action, date=date, chamber=actor, classification=atype
                )

        self.scrape_subjects(bill, bill_id, session, req_session)

        yield bill

    def get_session_id(self, session):
        return {
            "2011-2012": "84",
            "2013-2014": "85",
            "2015-2016": "86",
            "2017-2018": "87",
            "2019-2020": "88",
            "2021-2022": "89",
        }[session]
