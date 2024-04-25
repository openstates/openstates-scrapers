import pytz
import urllib
from datetime import datetime

from openstates.scrape import Scraper, Bill, VoteEvent

from utils import LXMLMixin


TIMEZONE = pytz.timezone("US/Central")


class NEBillScraper(Scraper, LXMLMixin):
    priority_bills = {}

    def scrape(self, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]
            self.info("no session specified, using %s", session["identifier"])
        else:
            session = next(
                (
                    item
                    for item in self.jurisdiction.legislative_sessions
                    if item["identifier"] == session
                ),
                None,
            )

        if session["classification"] == "special":
            yield from self.scrape_special(session["identifier"], session["start_date"])
        else:
            self.scrape_priorities()
            start_year = datetime.strptime(session["start_date"], "%Y-%m-%d").year
            end_year = datetime.strptime(session["end_date"], "%Y-%m-%d").year
            yield from self.scrape_year(session["identifier"], start_year)
            if start_year != end_year:
                yield from self.scrape_year(session["identifier"], end_year)

    def scrape_priorities(self):
        priority_url = "https://nebraskalegislature.gov/session/priority.php"
        page = self.lxmlize(priority_url)

        for row in page.xpath(
            "//table[@id='committee_bill_results' or @id='senator_bill_results' or @id='speaker_bill_results']/tr"
        ):
            bill_id = row.xpath("td[2]/a/text()")[0].strip()
            prioritizer = row.xpath("td[1]/text()")[0].strip()

            self.priority_bills[bill_id] = {
                "prioritizer": prioritizer,
            }

    # NE Specials are lumped in with regular data, just duped bill numbers.
    # Scrape by intro date, instead of by year.
    def scrape_special(self, session, start_date):
        main_url = (
            "https://nebraskalegislature.gov/bills/search_by_date.php?"
            "SessionDay={}".format(start_date)
        )
        page = self.lxmlize(main_url)

        document_links = self.get_nodes(
            page,
            '//div[@class="main-content"]//div[@class="table-responsive"]//'
            "table/tbody/tr/td[1]/a",
        )

        for document_link in document_links:
            # bill_number = document_link.text
            bill_link = document_link.attrib["href"]

            yield from self.bill_info(bill_link, session, main_url)

    def scrape_year(self, session, year):

        main_url = (
            "https://nebraskalegislature.gov/bills/search_by_date.php?"
            "SessionDay={}".format(year)
        )
        page = self.lxmlize(main_url)

        document_links = self.get_nodes(
            page,
            '//div[@class="main-content"]//div[contains(@class,"table-responsive")]//'
            'table[contains(@class,"table")]/tbody/tr/td[1]/a',
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
            bill_page, '//table[contains(@class,"history")]/tbody/tr'
        )

        actor = "legislature"
        for action_node in action_nodes:
            date = self.get_node(action_node, "./td[1]").text
            date = datetime.strptime(date, "%b %d, %Y")

            # The action node may have an anchor element within it, so
            # we grab all the text within.
            action = self.get_node(action_node, "./td[2]").text_content()

            # NE legislature site does not list cosponsors, so we grab it from action statements
            if "name added" in action:
                cosponsor_name = action.split("name added")[0].strip()
                bill.add_sponsorship(
                    cosponsor_name,
                    entity_type="person",
                    classification="cosponsor",
                    primary=False,
                )

            if "Governor" in action:
                actor = "executive"
            else:
                actor = "legislature"

            action_type = self.action_types(action)
            bill.add_action(
                action,
                date.strftime("%Y-%m-%d"),
                chamber=actor,
                classification=action_type,
            )

            if "Notice of hearing for" in action:
                ref_date = action.replace("Notice of hearing for", "").strip()
                bill.extras["NE_REF_DATE"] = ref_date

            if "Referred to" in action:
                ref_com = action.split("Referred to")[1].strip()
                bill.extras["NE_REF_COM"] = ref_com

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

        # Add amendments
        amendment_rows = self.get_nodes(
            bill_page,
            ".//div[contains(@class, 'amends') and .//a[contains(@href, '/AM/')]]",
        )

        for row in amendment_rows:
            if not row.xpath(".//p[contains(@class,'fw-bold')]"):
                continue
            status = (
                row.xpath(".//p[contains(@class,'fw-bold')]")[0].text_content().strip()
            )
            amendment_names = row.xpath(".//h6/a/text()")
            amendment_names = [name.strip() for name in amendment_names]
            amendment_name = " ".join(amendment_names)
            amendment_url = row.xpath(".//h6/a/@href")[0]
            # adopted amendments get added as versions, everything else goes into documents
            if "adopted" in status.lower():
                bill.add_version_link(
                    amendment_name, amendment_url, media_type="application/pdf"
                )
            else:
                amendment_name = f"{amendment_name} ({status})"
                bill.add_document_link(
                    amendment_name, amendment_url, media_type="application/pdf"
                )

        if bill_number in self.priority_bills:
            priority = self.priority_bills[bill_number]
            bill.extras["NE_PRIORITIZER"] = priority["prioritizer"]

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

            vote = VoteEvent(
                bill=bill,
                chamber=chamber,
                start_date=TIMEZONE.localize(date),
                motion_text=motion_text,
                classification="passage",
                result="pass" if passed else "fail",
            )

            yes_voters, yes_count = self.get_votes(vote_page, "Yes :")
            no_voters, no_count = self.get_votes(vote_page, "No :")
            exc_voters, exc_count = self.get_votes(vote_page, "Excused Not Voting:")
            abs_voters, absent_count = self.get_votes(vote_page, "Absent Not Voting:")
            pre_voters, present_count = self.get_votes(vote_page, "Present Not Voting:")

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("excused", exc_count)
            vote.set_count("absent", absent_count)
            vote.set_count("abstain", present_count)

            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(vote_url).query)
            vote.dedupe_key = query_params["KeyID"][0]
            vote.add_source(vote_url)

            for name in yes_voters:
                vote.yes(name)
            for name in no_voters:
                vote.no(name)
            for name in exc_voters:
                vote.vote("excused", name)
            for name in abs_voters:
                vote.vote("absent", name)
            for name in pre_voters:
                vote.vote("abstain", name)

            yield vote

    # Find the vote count row containing row_string, and return the integer count
    def get_votes(self, page, row_string):
        count_xpath = 'string(//div[@id="by_vote_viewport"]//div[contains(@class, "card-header")][contains(text(),"{}")])'
        count_text = page.xpath(count_xpath.format(row_string))
        value = "".join(x for x in count_text if x and x.isdigit())
        cells_xpath = (
            '//div[@id="by_vote_viewport"]//div[contains(@class, "card-header")][contains(text(),"{}")]'
            "/following-sibling::table//td/div/text()"
        )
        cells_xpath = page.xpath(cells_xpath.format(row_string))
        cells = [cell.strip() for cell in cells_xpath if cell.strip()]

        return cells, int(value) if value else 0

    def action_types(self, action):
        if "Date of introduction" in action:
            action_type = "introduction"
        elif "Referred to" in action:
            action_type = "referral-committee"
        elif "Indefinitely postponed" in action:
            action_type = "committee-failure"
        elif "Placed on General File" in action:
            action_type = "committee-passage"
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
        elif "Became law without Governor's signature" in action:
            action_type = "became-law"
        else:
            action_type = None
        return action_type
