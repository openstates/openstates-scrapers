import re
import datetime
import lxml.html
import requests
from openstates.scrape import Scraper, Bill
from .actions import Categorizer


class IABillScraper(Scraper):
    categorizer = Categorizer()

    def scrape(self, session=None, chamber=None, prefiles=None):
        self.retry_attempts = 3
        self.retry_wait_seconds = 6
        req_session = requests.Session()
        req_session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        # openstates/issues#252 - IA continues to prefile after session starts
        # so we'll continue scraping both
        # yield from self.scrape_prefiles(session)

        session_id = self.get_session_id(session)
        url = f"https://www.legis.iowa.gov/legislation/findLegislation/allbills?ga={session_id}"
        page = lxml.html.fromstring(req_session.get(url).text)

        for option in page.xpath("//*[@id='sortableTable']/tbody/tr"):
            bill_id = option.xpath("td[2]/a/text()")[0]
            title = option.xpath("td[3]/text()")[0].split("(")[0]
            chamber = "lower" if bill_id[0] == "H" else "upper"
            sponsors = option.xpath("td[6]/text()")[0]

            bill_url = f"https://www.legis.iowa.gov/legislation/BillBook?ga={session_id}&ba={bill_id.replace(' ', '')}"

            yield self.scrape_bill(
                chamber, session, session_id, bill_id, bill_url, title, sponsors
            )

    # IA does prefiles on a separate page, with no bill numbers,
    # after introduction they'll link bill numbers to the prefile doc id
    def scrape_prefiles(self, session):
        prefile_url = (
            "https://www.legis.iowa.gov/legislation/billTracking/prefiledBills"
        )
        page = lxml.html.fromstring(self.get(prefile_url).content)
        page.make_links_absolute(prefile_url)

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

            bill.add_source(prefile_url)

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

    def scrape_bill(self, chamber, session, session_id, bill_id, url, title, sponsors):
        req_session = requests.Session()
        req_session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        try:
            sidebar = lxml.html.fromstring(self.get(url, cookies=self.cookies).text)
            sidebar.make_links_absolute("https://www.legis.iowa.gov")
        except requests.exceptions.ConnectionError:
            self.warning("Connection closed without response, skipping")
            return

        hist_url = (
            f"https://www.legis.iowa.gov/legislation/billTracking/"
            f"billHistory?billName={bill_id}&ga={session_id}"
        )
        req = req_session.get(hist_url)
        if req.status_code == 500:
            self.warning("500 error on {}, skipping".format(hist_url))
            return

        page = lxml.html.fromstring(req.text)
        page.make_links_absolute("https://www.legis.iowa.gov")

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

        sponsor_array = sponsors.replace("and", ",").split(",")

        for sponsor in sponsor_array:
            bill.add_sponsorship(
                name=sponsor.strip(),
                classification="primary",
                entity_type="organization" if "COMMITTEE ON" in sponsor else "person",
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
                for anchor in tr.xpath(".//a"):
                    link_text = anchor.text_content()
                    link_url = anchor.xpath("@href")[0]
                    if "signed" in link_text.lower():
                        bill.add_version_link(
                            note=link_text, url=link_url, media_type="application/pdf"
                        )
                    elif "acts" in link_text.lower():
                        bill.add_document_link(
                            note=link_text, url=link_url, media_type="application/pdf"
                        )
                        bill.add_citation(
                            f"IA Acts, {session}",
                            link_text.replace("Acts", ""),
                            citation_type="chapter",
                            url=link_url,
                        )
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
            else:
                for anchor in tr.xpath(".//a"):
                    link_text = anchor.text_content()
                    link_url = anchor.xpath("@href")[0]
                    action_date = date.strftime("%m/%d/%Y")
                    if "fiscal" in link_text.lower() or "summary" in link_text.lower():
                        # there can be multiple fiscal notes or summaries, so date them
                        doc_title = f"{link_text} {action_date}"
                        bill.add_document_link(
                            note=doc_title, url=link_url, media_type="application/pdf"
                        )
                    elif "signed" in link_text.lower():
                        bill.add_version_link(
                            note=link_text, url=link_url, media_type="application/pdf"
                        )
                    elif "acts" in link_text.lower():
                        bill.add_document_link(
                            note=link_text, url=link_url, media_type="application/pdf"
                        )
                        bill.add_citation(
                            f"IA Acts, {session}",
                            link_text.replace("Acts", ""),
                            citation_type="chapter",
                            url=link_url,
                        )

            if "S.J." in action or "SCS" in action:
                actor = "upper"
            elif "H.J." in action or "HCS" in action:
                actor = "lower"
            else:
                actor = "legislature"

            action = re.sub(r"(H|S)\.J\.\s+\d+\.$", "", action).strip()

            action_attr = self.categorizer.categorize(action.lower())
            atype = action_attr["classification"]

            if action.strip() == "":
                continue

            if re.search(r"END OF \d+ ACTIONS", action):
                continue

            if "$history" not in action:
                bill.add_action(
                    description=action, date=date, chamber=actor, classification=atype
                )

        # self.scrape_subjects(bill, bill_id, session, req_session)

        yield bill

    def get_session_id(self, session):
        # https://www.legis.iowa.gov/legislation/BillBook
        # select[@name="gaList"]
        return {
            "2011-2012": "84",
            "2013-2014": "85",
            "2015-2016": "86",
            "2017-2018": "87",
            "2019-2020": "88",
            "2021-2022": "89",
            "2023-2024": "90",
        }[session]
