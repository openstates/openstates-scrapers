import pytz
import urllib
from datetime import datetime

from openstates_core.scrape import Scraper, Bill, VoteEvent

from openstates.utils import LXMLMixin


TIMEZONE = pytz.timezone("US/Central")
VOTE_TYPE_MAP = {"yes": "yes", "no": "no"}


class NEBillScraper(Scraper, LXMLMixin):
    def scrape(self, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]
            self.info("no session specified, using %s", session["identifier"])
        start_year = datetime.strptime(session["start_date"], "%Y-%m-%d").year
        end_year = datetime.strptime(session["end_date"], "%Y-%m-%d").year
        yield from self.scrape_year(session["identifier"], start_year)
        if start_year != end_year:
            yield from self.scrape_year(session["identifier"], end_year)

    def scrape_year(self, session, year):

        main_url = (
            "https://nebraskalegislature.gov/bills/search_by_date.php?"
            "SessionDay={}".format(year)
        )
        page = self.lxmlize(main_url)

        document_links = self.get_nodes(
            page,
            '//div[@class="main-content"]//div[@class="table-responsive"]//'
            'table[@class="table"]/tbody/tr/td[1]/a',
        )

        for document_link in document_links:
            # bill_number = document_link.text
            bill_link = document_link.attrib["href"]

            # POST request for search form
            # post_dict = {'DocumentNumber': bill_number, 'Legislature': session}
            # headers = urllib.urlencode(post_dict)
            # bill_resp = self.post('http://nebraskalegislature.gov/bills/'
            #     'search_by_number.php', data=post_dict)
            # bill_link = bill_resp.url
            # bill_page = bill_resp.text

            yield from self.bill_info(bill_link, session, main_url)

    def bill_info(self, bill_link, session, main_url):
        bill_page = self.lxmlize(bill_link)

        long_title = self.get_node(
            bill_page, '//div[@class="main-content"]//h2'
        ).text.split()

        bill_number = long_title[0]
        title = ""
        for x in range(2, len(long_title)):
            title += long_title[x] + " "
        title = title[0:-1]

        if not title:
            self.error("no title, skipping %s", bill_number)
            return

        bill_type = "resolution" if "LR" in bill_number else "bill"

        bill = Bill(bill_number, session, title, classification=bill_type)

        bill.add_source(main_url)
        bill.add_source(bill_link)

        introduced_by = self.get_node(
            bill_page,
            "//body/div[3]/div[2]/div[2]/div/div[3]/div[1]/ul/li[1]/a[1]/text()",
        )

        if not introduced_by:
            introduced_by = self.get_node(
                bill_page,
                "//body/div[3]/div[2]/div[2]/div/div[2]/div[1]/ul/li[1]/text()",
            )
            introduced_by = introduced_by.split("Introduced By:")[1].strip()

        introduced_by = introduced_by.strip()
        bill.add_sponsorship(
            name=introduced_by,
            entity_type="person",
            primary=True,
            classification="primary",
        )

        action_nodes = self.get_nodes(
            bill_page, '//div[@class="main-content"]/div[5]//table/tbody/tr'
        )

        for action_node in action_nodes:
            date = self.get_node(action_node, "./td[1]").text
            date = datetime.strptime(date, "%b %d, %Y")

            # The action node may have an anchor element within it, so
            # we grab all the text within.
            action = self.get_node(action_node, "./td[2]").text_content()

            if "Governor" in action:
                actor = "executive"
            elif "Speaker" in action:
                actor = "legislature"
            else:
                actor = "legislature"

            action_type = self.action_types(action)
            bill.add_action(
                action,
                date.strftime("%Y-%m-%d"),
                chamber=actor,
                classification=action_type,
            )

        # Grabs bill version documents.
        version_links = self.get_nodes(
            bill_page, "/html/body/div[3]/div[2]/div[2]/div/" "div[3]/div[2]/ul/li/a"
        )

        for version_link in version_links:
            version_name = version_link.text
            version_url = version_link.attrib["href"]
            # replace Current w/ session number
            version_url = version_url.replace("Current", session)
            bill.add_version_link(
                version_name, version_url, media_type="application/pdf"
            )

        soi = self.get_nodes(bill_page, ".//a[contains(text(), 'Statement of Intent')]")
        if soi:
            bill.add_document_link(
                "Statement of Intent", soi[0].get("href"), media_type="application/pdf"
            )
        comstmt = self.get_nodes(
            bill_page, ".//a[contains(text(), 'Committee Statement')]"
        )
        if comstmt:
            bill.add_document_link(
                "Committee Statement",
                comstmt[0].get("href"),
                media_type="application/pdf",
            )
        fn = self.get_nodes(bill_page, ".//a[contains(text(), 'Fiscal Note')]")
        if fn:
            bill.add_document_link(
                "Fiscal Note", fn[0].get("href"), media_type="application/pdf"
            )

        # Adds any documents related to amendments.
        amendment_links = self.get_nodes(
            bill_page, ".//div[contains(@class, 'amend-link')]/a"
        )

        for amendment_link in amendment_links:
            amendment_name = amendment_link.text
            amendment_url = amendment_link.attrib["href"]
            # skip over transcripts
            if "/AM/" not in amendment_url:
                continue
            bill.add_document_link(
                amendment_name, amendment_url, media_type="application/pdf"
            )

        yield bill

        yield from self.scrape_votes(bill, bill_page, actor)

    def scrape_amendments(self, bill, bill_page):
        amd_xpath = '//div[contains(@class,"amends") and not(contains(@class,"mb-3"))]'
        for row in bill_page.xpath(amd_xpath):
            status = row.xpath("string(./div[2])").strip()
            if "adopted" in status.lower():
                version_url = row.xpath("./div[1]/a/@href")[0]
                version_name = row.xpath("./div[1]/a/text()")[0]
                bill.add_version_link(
                    version_name,
                    version_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

    def scrape_votes(self, bill, bill_page, chamber):
        vote_links = bill_page.xpath(
            '//table[contains(@class,"history")]//a[contains(@href, "view_votes")]'
        )
        for vote_link in vote_links:
            vote_url = vote_link.attrib["href"]
            date_td, motion_td, *_ = vote_link.xpath("ancestor::tr/td")
            date = datetime.strptime(date_td.text, "%b %d, %Y")
            motion_text = motion_td.text_content()
            vote_page = self.lxmlize(vote_url)
            passed = "Passed" in motion_text or "Advanced" in motion_text
            cells = vote_page.xpath(
                '//div[contains(@class,"table-responsive")]/table//td'
            )
            vote = VoteEvent(
                bill=bill,
                chamber=chamber,
                start_date=TIMEZONE.localize(date),
                motion_text=motion_text,
                classification="passage",
                result="pass" if passed else "fail",
            )

            yes_count = self.process_count(vote_page, "Yes:")
            no_count = self.process_count(vote_page, "No:")
            exc_count = self.process_count(vote_page, "Excused - Not Voting:")
            absent_count = self.process_count(vote_page, "Absent - Not Voting:")
            present_count = self.process_count(vote_page, "Present - Not Voting:")

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("excused", exc_count)
            vote.set_count("absent", absent_count)
            vote.set_count("abstain", present_count)

            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(vote_url).query)
            vote.pupa_id = query_params["KeyID"][0]
            vote.add_source(vote_url)
            for chunk in range(0, len(cells), 2):
                name = cells[chunk].text
                vote_type = cells[chunk + 1].text
                if name and vote_type:
                    vote.vote(VOTE_TYPE_MAP.get(vote_type.lower(), "other"), name)
            yield vote

    # Find the vote count row containing row_string, and return the integer count
    def process_count(self, page, row_string):
        count_xpath = (
            'string(//ul[contains(@class,"list-unstyled")]/li[contains(text(),"{}")])'
        )
        count_text = page.xpath(count_xpath.format(row_string))
        return int("".join(x for x in count_text if x.isdigit()))

    def action_types(self, action):
        if "Date of introduction" in action:
            action_type = "introduction"
        elif "Referred to" in action:
            action_type = "referral-committee"
        elif "Indefinitely postponed" in action:
            action_type = "committee-failure"
        elif ("File" in action) or ("filed" in action):
            action_type = "filing"
        elif "Placed on Final Reading" in action:
            action_type = "reading-3"
        elif "Passed" in action or "President/Speaker signed" in action:
            action_type = "passage"
        elif "Presented to Governor" in action:
            action_type = "executive-receipt"
        elif "Approved by Governor" in action:
            action_type = "executive-signature"
        elif "Failed to pass notwithstanding the objections of the Governor" in action:
            action_type = "executive-veto"
        elif "Failed" in action:
            action_type = "failure"
        elif "Bill withdrawn" in action:
            action_type = "withdrawal"
        else:
            action_type = None
        return action_type
