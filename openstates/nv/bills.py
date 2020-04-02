import re
import pytz
import time
from datetime import datetime
from collections import defaultdict
import lxml.html
from openstates.utils.lxmlize import LXMLMixin
from openstates_core.scrape import Scraper, Bill
import requests
from urllib.parse import unquote


class NVBillScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("PST8PDT")
    _classifiers = (
        ("Approved by the Governor", "executive-signature"),
        ("Bill read. Veto not sustained", "veto-override-passage"),
        ("Bill read. Veto sustained", "veto-override-failure"),
        ("Enrolled and delivered to Governor", "executive-receipt"),
        ("From committee: .+? adopted", "committee-passage"),
        ("From committee: .+? pass", "committee-passage"),
        ("Prefiled. Referred", ["introduction", "referral-committee"]),
        ("Read first time. Referred", ["reading-1", "referral-committee"]),
        ("Read first time.", "reading-1"),
        ("Read second time.", "reading-2"),
        ("Read third time. Lost", ["failure", "reading-3"]),
        ("Read third time. Passed", ["passage", "reading-3"]),
        ("Read third time.", "reading-3"),
        ("Rereferred", "referral-committee"),
        ("Resolution read and adopted", "passage"),
        ("Vetoed by the Governor", "executive-veto"),
    )

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber else ["upper", "lower"]
        self._seen_votes = set()
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):

        session_slug = self.jurisdiction.session_slugs[session]
        if "Special" in session_slug:
            year = session_slug[4:8]
        elif int(session_slug[:2]) >= 71:
            year = ((int(session_slug[:2]) - 71) * 2) + 2001
        else:
            return "No data exists for %s" % session

        self.subject_mapping = defaultdict(list)
        if "Special" not in session_slug:
            self.scrape_subjects(session_slug, session, year)

        yield from self.scrape_bills(chamber, session_slug, session, year)

    def scrape_subjects(self, insert, session, year):
        url = (
            "http://www.leg.state.nv.us/Session/%s/Reports/"
            "TablesAndIndex/%s_%s-index.html" % (insert, year, session)
        )

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # first, a bit about this page:
        # Level0 are the bolded titles
        # Level1,2,3,4 are detailed titles, contain links to bills
        # all links under a Level0 we can consider categorized by it
        # there are random newlines *everywhere* that should get replaced

        subject = None

        for p in doc.xpath("//p"):
            if p.get("class") == "Level0":
                subject = p.text_content().replace("\r\n", " ")
            else:
                if subject:
                    for a in p.xpath(".//a"):
                        bill_id = a.text.replace("\r\n", "") if a.text else None
                        self.subject_mapping[bill_id].append(subject)

    def scrape_bills(self, chamber, session_slug, session, year):
        doc_types = {
            "lower": ["AB", "IP", "AJR", "ACR", "AR"],
            "upper": ["SB", "SJR", "SCR", "SR"],
        }

        for doc_type in doc_types[chamber]:
            bill_list_url = f"https://www.leg.state.nv.us/App/NELIS/REL/{session_slug}/HomeBill/BillsTab?Filters."
            "SearchText=&Filters.SelectedBillTypes={doc_type}&Filters.DisplayTitles=false&Filters.PageSize=2147483647"
            try:
                listing_page = lxml.html.fromstring(self.get(bill_list_url).text)
                listing_page.make_links_absolute("https://www.leg.state.nv.us")
                bill_row_xpath = (
                    "//div[@class='home-listing bill-listing top-margin-med']//a"
                )
                for row in listing_page.xpath(bill_row_xpath):
                    link_url = row.xpath("@href")[0]
                    yield self.scrape_bill(session, session_slug, chamber, link_url)
            except requests.exceptions.RequestException:
                self.warning("failed to fetch bill listing page")

    def scrape_bill(self, session, session_slug, chamber, url):
        page = lxml.html.fromstring(self.get(url).text)
        bill_no = page.xpath('//*[@id="item-header"]/text()')[0].strip()
        # state bill id
        internal_id = re.search(r"\/Bill\/(\d+)\/Overview", url).group(1)

        # bill data gets filled in from another call
        bill_data_base = (
            "https://www.leg.state.nv.us/App/NELIS/REL/{}/Bill/"
            "FillSelectedBillTab?selectedTab=Overview&billKey={}&_={}"
        )
        bill_data_url = bill_data_base.format(
            session_slug, internal_id, time.time() * 1000
        )

        bill_page = lxml.html.fromstring(self.get(bill_data_url).text)

        short_title = self.get_header_field(bill_page, "Summary:").text
        short_title = short_title.replace("\u00a0", " ")

        bill = Bill(
            identifier=bill_no,
            legislative_session=session,
            title=short_title,
            chamber=chamber,
        )

        long_title = self.get_header_field(bill_page, "Title:").text
        if long_title is not None:
            bill.add_abstract(long_title, "Summary")

        sponsor_div = self.get_header_field(bill_page, "Primary Sponsor")
        if sponsor_div is not None:
            self.add_sponsors(sponsor_div, bill, "primary")

        cosponsor_div = self.get_header_field(bill_page, "Co-Sponsor")
        if cosponsor_div is not None:
            self.add_sponsors(cosponsor_div, bill, "cosponsor")

        self.add_actions(bill_page, bill, chamber)
        self.add_versions(session_slug, internal_id, bill)

        bill.subject = list(set(self.subject_mapping[bill_no]))

        bdr = self.extract_bdr(short_title)
        if bdr:
            bill.extras["BDR"] = bdr

        bill.extras["NV_ID"] = internal_id

        bill.add_source(url)
        yield bill

    def add_sponsors(self, page, bill, classification):
        seen = []
        person_sponsors = page.xpath('.//a[@class="bio"]/text()')
        for leg in person_sponsors:
            name = leg.strip()
            if name not in seen:
                seen.append(name)
                bill.add_sponsorship(
                    name=name,
                    classification=classification,
                    entity_type="person",
                    primary=True,
                )

        com_sponsors = page.xpath('.//a[contains(@href, "/Committee/")]/text()')
        for com in com_sponsors:
            name = com.strip()
            if name not in seen:
                seen.append(name)
                bill.add_sponsorship(
                    name=name,
                    classification=classification,
                    entity_type="organization",
                    primary=True,
                )

    def get_header_field(self, page, title_text):
        # NV bill page has the same structure for lots of fields
        # this finds field content after the div containing title_text
        # We're returning the element and not the text,
        # because sometimes we need to parse the html
        header_xpath = (
            '//div[./div[contains(text(), "{}")]]'
            '/div[contains(@class, "col-sm-10") or contains(@class, "col-xs-10")]'.format(
                title_text
            )
        )
        if page.xpath(header_xpath):
            return page.xpath(header_xpath)[0]
        else:
            return None

    def add_versions(self, session_slug, internal_id, bill):
        text_tab_url_base = (
            "https://www.leg.state.nv.us/App/NELIS/REL/{}/Bill/"
            "FillSelectedBillTab?selectedTab=Text&billKey={}&_={}"
        )
        text_tab_url = text_tab_url_base.format(
            session_slug, internal_id, time.time() * 1000
        )
        text_page = lxml.html.fromstring(self.get(text_tab_url).text)

        version_links = text_page.xpath('//*[contains(@class,"text-revision-link")]')
        for link in version_links:
            document_key = link.get("id")
            if link.tag == "input":
                document_name = link.get("value")
            elif link.tag == "a":
                document_name = link.text.strip()

            iframe_url_base = (
                "https://www.leg.state.nv.us/App/NELIS/REL/{}/Bill/"
                "DisplayBillText?billDocumentKey={}&_={}"
            )
            iframe_url = iframe_url_base.format(
                session_slug, document_key, time.time() * 1000
            )

            iframe_page = lxml.html.fromstring(self.get(iframe_url).text)

            # web-accessible filename is the final URL arg (encoded) in the iframe's SRC:
            # /App/NELIS/REL/80th2019/PDF/Viewer?
            # file=%2FApp%2FNELIS%2FREL%2F80th2019%2FDocumentViewer%2FRemoteURLDocument%3F
            # remoteURL%3Dhttps%253A%252F%252Fwww.leg.state.nv.us%252FSession%252F80th2019%252FBills%252FSB%252FSB1.pdf
            # %26downloadFileName%3DSB1.pdf&downloadFileName=SB1.pdf
            # here:
            # &remoteURL=https%3A%2F%2Fwww.leg.state.nv.us%2FSession%2F80th2019%2FBills%2FSB%2FSB1.pdf

            if iframe_page.xpath('//iframe[@id="pdf-viewer"]/@src'):
                iframe = iframe_page.xpath('//iframe[@id="pdf-viewer"]/@src')[0]
                parts = iframe.split("remoteURL=")
                if len(parts) > 1:
                    doc_url = parts[1]
                    doc_url = unquote(doc_url)
                    bill.add_version_link(
                        document_name,
                        doc_url,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

    def add_actions(self, page, bill, chamber):
        actor = chamber

        for tr in page.xpath('//tbody[@class="bill-history"]/tr'):

            action_date = tr.xpath("td[1]/text()")[0].strip()
            action_date = datetime.strptime(action_date, "%b %d, %Y")
            action_date = self._tz.localize(action_date)
            action = tr.xpath("td[2]/text()")[0].strip().replace("\u00a0", " ")
            # catch chamber changes
            if action.startswith("In Assembly"):
                actor = "lower"
            elif action.startswith("In Senate"):
                actor = "upper"
            elif "Governor" in action:
                actor = "executive"

            action_type = None
            for pattern, atype in self._classifiers:
                if re.match(pattern, action):
                    action_type = atype
                    break

            if "Committee on" in action:
                committees = re.findall(r"Committee on ([a-zA-Z, ]*)\.", action)
                if len(committees) > 0:
                    related_entities = []
                    for committee in committees:
                        related_entities.append(
                            {"type": "committee", "name": committee}
                        )
                    bill.add_action(
                        description=action,
                        date=action_date,
                        chamber=actor,
                        classification=action_type,
                        related_entities=related_entities,
                    )
                    continue

            bill.add_action(
                description=action,
                date=action_date,
                chamber=actor,
                classification=action_type,
            )

    def add_fiscal_notes(self, session_slug, internal_id, bill):
        text_tab_url_base = (
            "https://www.leg.state.nv.us/App/NELIS/REL/{}/Bill/"
            "FillSelectedBillTab?selectedTab=FiscalNotes&billKey={}&_={}"
        )
        text_tab_url = text_tab_url_base.format(
            session_slug, internal_id, time.time() * 1000
        )
        text_page = lxml.html.fromstring(self.get(text_tab_url).text)

        note_links = text_page.xpath('//a[contains(@class,"text-icon-exhibit")]')
        for link in note_links:
            name = link.text_content().strip()
            name = "Fiscal Note: {}".format(name)
            url = link.get("href")
            bill.add_document_link(
                note=name, url=url, media_type="application/pdf", on_duplicate="ignore"
            )

    # def scrape_votes(self, bill_page, page_url, bill, insert, year):
    #     root = lxml.html.fromstring(bill_page)
    #     trs = root.xpath('/html/body/div/table[6]//tr')
    #     assert len(trs) >= 1, "Didn't find the Final Passage Votes' table"

    #     for tr in trs[1:]:
    #         links = tr.xpath('td/a[contains(text(), "Passage")]')
    #         if len(links) == 0:
    #             self.warning("Non-passage vote found for {}; ".format(bill.identifier) +
    #                          "probably a motion for the calendar. It will be skipped.")
    #         else:
    #             assert len(links) == 1, \
    #                 "Too many votes found for XPath query, on bill {}".format(bill.identifier)
    #             link = links[0]

    #         motion = link.text
    #         if 'Assembly' in motion:
    #             chamber = 'lower'
    #         else:
    #             chamber = 'upper'

    #         votes = {}
    #         tds = tr.xpath('td')
    #         for td in tds:
    #             if td.text:
    #                 text = td.text.strip()
    #                 date = re.match('... .*?, ....', text)
    #                 count = re.match('(?P<category>.*?) (?P<votes>[0-9]+)[,]?', text)
    #                 if date:
    #                     vote_date = datetime.strptime(text, '%b %d, %Y')
    #                 elif count:
    #                     votes[count.group('category')] = int(count.group('votes'))

    #         yes = votes['Yea']
    #         no = votes['Nay']
    #         excused = votes['Excused']
    #         not_voting = votes['Not Voting']
    #         absent = votes['Absent']
    #         other = excused + not_voting + absent
    #         passed = yes > no

    #         vote = VoteEvent(chamber=chamber, start_date=self._tz.localize(vote_date),
    #                          motion_text=motion, result='pass' if passed else 'fail',
    #                          classification='passage', bill=bill,
    #                          )
    #         vote.set_count('yes', yes)
    #         vote.set_count('no', no)
    #         vote.set_count('other', other)
    #         vote.set_count('not voting', not_voting)
    #         vote.set_count('absent', absent)
    #         # try to get vote details
    #         try:
    #             vote_url = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (
    #                 insert, link.get('href'))
    #             vote.pupa_id = vote_url
    #             vote.add_source(vote_url)

    #             if vote_url in self._seen_votes:
    #                 self.warning('%s is included twice, skipping second', vote_url)
    #                 continue
    #             else:
    #                 self._seen_votes.add(vote_url)

    #             page = self.get(vote_url).text
    #             page = page.replace(u"\xa0", " ")
    #             root = lxml.html.fromstring(page)

    #             for el in root.xpath('//table[2]/tr'):
    #                 tds = el.xpath('td')
    #                 name = tds[1].text_content().strip()
    #                 vote_result = tds[2].text_content().strip()

    #                 if vote_result == 'Yea':
    #                     vote.yes(name)
    #                 elif vote_result == 'Nay':
    #                     vote.no(name)
    #                 else:
    #                     vote.vote('other', name)
    #             vote.add_source(page_url)
    #         except scrapelib.HTTPError:
    #             self.warning("failed to fetch vote page, adding vote without details")

    #         yield vote

    # bills in NV start with a 'bill draft request'
    # the number is in the title but it's useful as a structured extra
    def extract_bdr(self, title):
        bdr = False
        bdr_regex = re.search(r"\(BDR (\w+\-\w+)\)", title)
        if bdr_regex:
            bdr = bdr_regex.group(1)
        return bdr
