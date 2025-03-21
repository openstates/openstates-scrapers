import re
import pytz
import datetime as dt
from collections import defaultdict

import lxml.html
import lxml.etree
from openstates.scrape import Scraper, Bill, VoteEvent

from utils import LXMLMixin

from .utils import clean_text, house_get_actor_from_action, senate_get_actor_from_action

bill_types = {
    "HB ": "bill",
    "HJR": "joint resolution",
    "HCR": "concurrent resolution",
    "SB ": "bill",
    "SJR": "joint resolution",
    "SCR": "concurrent resolution",
}

TIMEZONE = pytz.timezone("America/Chicago")


class UnrecognizedSessionType(BaseException):
    def __init__(self, session):
        super().__init__(f"Session {session} has the unrecognized session types.")


class MOBillScraper(Scraper, LXMLMixin):
    _house_base_url = "https://www.house.mo.gov"
    # List of URLS that aren't working when we try to visit them (but
    # probably should work):
    _bad_urls = []
    _subjects = defaultdict(list)
    _session_id = ""

    def custom_header_func(self, url):
        return {"user-agent": "openstates.org"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super(Scraper, self).__init__(header_func=self.custom_header_func)

    def _get_action(self, actor, action):
        # Alright. This covers both chambers and everything else.
        flags = [
            ("Introduced", "introduction"),
            ("Offered", "introduction"),
            ("First Read", "reading-1"),
            ("Read Second Time", "reading-2"),
            ("Second Read", "reading-2"),
            # make sure passage is checked before reading-3
            ("Third Read and Passed", "passage"),
            ("Reported Do Pass", "committee-passage"),
            ("Voted Do Pass", "committee-passage"),
            ("Third Read", "reading-3"),
            ("Referred", "referral-committee"),
            ("Withdrawn", "withdrawal"),
            ("S adopted", "passage"),
            ("Truly Agreed To and Finally Passed", "passage"),
            ("Signed by Governor", "executive-signature"),
            ("Approved by Governor", "executive-signature"),
            ("Vetoed by Governor", "executive-veto"),
            ("Vetoed in Part by Governor", "executive-veto-line-item"),
            ("Legislature voted to override Governor's veto", "veto-override-passage"),
        ]
        categories = []
        for flag, acat in flags:
            if flag in action:
                categories.append(acat)

        return categories or None

    def _get_session_code(self, session):
        # R or S1
        year = session[2:]
        if len(session) == 4:
            return f"{year}1"
        elif "S1" in session:
            return f"{year}3"
        elif "S2" in session:
            return f"{year}4"
        else:
            raise UnrecognizedSessionType(session)

    def _get_votes(self, date, actor, action, bill, url):
        vre = r"(?P<leader>.*)(AYES|YEAS):\s+(?P<yeas>\d+)\s+(NOES|NAYS):\s+(?P<nays>\d+).*"
        if "YEAS" in action.upper() or "AYES" in action.upper():
            match = re.match(vre, action)
            if match:
                v = match.groupdict()
                yes, no = int(v["yeas"]), int(v["nays"])
                vote = VoteEvent(
                    chamber=actor,
                    motion_text=v["leader"],
                    result="pass" if yes > no else "fail",
                    classification="passage",
                    start_date=TIMEZONE.localize(date),
                    bill=bill,
                )
                vote.add_source(url)
                yield vote

    def _parse_cosponsors_from_bill(self, bill, url):
        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        table = bill_page.xpath('//table[@id="CoSponsorTable"]')
        assert len(table) == 1
        for row in table[0].xpath("./tr"):
            name = row[0].text_content()
            if re.search(r"no co-sponsors", name, re.IGNORECASE):
                continue
            bill.add_sponsorship(
                row[0].text_content(),
                entity_type="person",
                classification="cosponsor",
                primary=False,
            )

    def session_type(self, session):
        # R or S1
        if len(session) == 4:
            return "R"
        elif "S1" in session:
            return "E1"
        elif "S2" in session:
            return "E2"
        else:
            self.error("Unrecognized Session Type")

    def _scrape_senate_subjects(self, session):
        self.info("Collecting subject tags from upper house.")

        subject_list_url = (
            "https://www.senate.mo.gov/{}info/BTS_Web/"
            "Keywords.aspx?SessionType={}".format(
                session[2:4], self.session_type(session)
            )
        )
        subject_page = self.lxmlize(subject_list_url)

        # Create a list of all possible bill subjects.
        subjects = self.get_nodes(subject_page, "//h3")

        for subject in subjects:
            subject_text = self.get_node(
                subject, "./a[string-length(text()) > 0]/text()[normalize-space()]"
            )
            subject_text = re.sub(r"([\s]*\([0-9]+\)$)", "", subject_text)

            # Bills are in hidden spans after the subject labels.
            bill_ids = subject.getnext().xpath("./b/a/text()[normalize-space()]")

            for bill_id in bill_ids:
                self._subjects[bill_id].append(subject_text)

    def _parse_senate_billpage(self, bill_url, year):
        bill_page = self.lxmlize(bill_url)

        # get all the info needed to record the bill
        # TODO probably still needs to be fixed
        bill_id = bill_page.xpath('//*[@id="lblBillNum"]')[0].text_content()
        bill_title = bill_page.xpath('//*[@id="lblBillTitle"]')[0].text_content()
        bill_desc = bill_page.xpath('//*[@id="lblBriefDesc"]')[0].text_content()
        # bill_lr = bill_page.xpath('//*[@id="lblLRNum"]')[0].text_content()

        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self._subjects:
            subs = self._subjects[bid]

        if bid == "XXXXXX":
            self.warning(f"Skipping Junk Bill {bid}")
            return

        bill = Bill(
            bill_id,
            title=bill_desc,
            chamber="upper",
            legislative_session=self._session_id,
            classification=bill_type,
        )
        bill.subject = subs
        bill.add_abstract(bill_desc, note="abstract")
        bill.add_source(bill_url)

        if bill_title:
            bill.add_title(bill_title)

        # Get the primary sponsor
        try:
            sponsor = bill_page.xpath('//a[@id="hlSponsor"]')[0]
        except IndexError:
            sponsor = bill_page.xpath('//span[@id="lSponsor"]')[0]

        bill_sponsor = sponsor.text_content()

        bill_sponsor_link = sponsor.attrib.get("href")

        if "Senators" in bill_sponsor_link:
            chamber = "upper"
        else:
            chamber = None

        bill.add_sponsorship(
            bill_sponsor,
            entity_type="person",
            classification="primary",
            primary=True,
            chamber=chamber,
        )

        # cosponsors show up on their own page, if they exist
        cosponsor_tag = bill_page.xpath('//a[@id="hlCoSponsors"]')
        if len(cosponsor_tag) > 0 and cosponsor_tag[0].attrib.get("href"):
            self._parse_senate_cosponsors(bill, cosponsor_tag[0].attrib["href"])

        # get the actions
        action_url = bill_page.xpath('//a[@id="hlAllActions"]')
        if len(action_url) > 0 and action_url[0].xpath("@href"):
            action_url = action_url[0].attrib["href"]
            self._parse_senate_actions(bill, action_url)

        # stored on a separate page
        versions_url = bill_page.xpath('//a[@id="hlFullBillText"]')
        if len(versions_url) > 0 and versions_url[0].attrib.get("href"):
            self._parse_senate_bill_versions(bill, versions_url[0].attrib["href"])

        amendment_links = bill_page.xpath('//a[contains(@href,"ShowAmendment.asp")]')
        for link in amendment_links:
            link_text = link.xpath("string(.)").strip()
            if not link_text:
                link_text = "Missing description"
            if "adopted" in link_text.lower():
                link_url = link.xpath("@href")[0]
                bill.add_version_link(
                    link_text,
                    link_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                    classification="amendment",
                )

        yield bill

    def _parse_senate_bill_versions(self, bill, url):
        bill.add_source(url)
        versions_page = self.get(url).text
        versions_page = lxml.html.fromstring(versions_page)
        version_tags = versions_page.xpath("//li/font/a")

        # some pages are updated and use different structure
        if not version_tags:
            version_tags = versions_page.xpath("//tr/td/a")

        for version_tag in version_tags:
            description = version_tag.text_content().strip()
            pdf_url = version_tag.attrib["href"]

            # MO seems to have busted HTML: tag ends with forward slash making it incorrectly self-closed
            # eg <a href='https://www.senate.mo.gov/25info/pdf-bill/intro/SB40.pdf'/>Introduced</a>
            # so text_content() fails to work as expected. Content is in tail property
            if description == "":
                description = version_tag.tail.strip()

            if description == "" and "intro" in pdf_url:
                description = "Introduced"
            elif not description:
                description = "Missing description"

            if pdf_url.endswith("pdf"):
                mimetype = "application/pdf"
            else:
                mimetype = None
            bill.add_version_link(
                description,
                pdf_url,
                media_type=mimetype,
                on_duplicate="ignore",
            )

    def _parse_senate_actions(self, bill, url):
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        bigtable = actions_page.xpath(
            "/html/body/font/form/table/tr[3]/td/div/table/tr"
        )

        for row in bigtable:
            date = row[0].text_content()
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            action = row[1].text_content()
            actor = senate_get_actor_from_action(action)
            type_class = self._get_action(actor, action)
            bill.add_action(
                action,
                TIMEZONE.localize(date),
                chamber=actor,
                classification=type_class,
            )

    def _parse_senate_cosponsors(self, bill, url):
        bill.add_source(url)
        cosponsors_page = self.get(url).text
        cosponsors_page = lxml.html.fromstring(cosponsors_page)
        # cosponsors are all in a table
        cosponsors = cosponsors_page.xpath('//table[@id="dgCoSponsors"]/tr/td/a')

        for cosponsor_row in cosponsors:
            # cosponsors include district, so parse that out
            cosponsor_string = cosponsor_row.text_content()
            cosponsor = clean_text(cosponsor_string)
            cosponsor = cosponsor.split(",")[0]

            # they give us a link to the congressperson, so we might
            # as well keep it.
            if cosponsor_row.attrib.get("href"):
                # cosponsor_url = cosponsor_row.attrib['href']
                bill.add_sponsorship(
                    cosponsor,
                    entity_type="person",
                    classification="cosponsor",
                    primary=False,
                )
            else:
                bill.add_sponsorship(
                    cosponsor,
                    entity_type="person",
                    classification="cosponsor",
                    primary=False,
                )

    def _scrape_upper_chamber(self, session):
        self.info("Scraping bills from upper chamber.")

        year2 = "%02d" % (int(session[:4]) % 100)

        # Save the root URL, since we'll use it later.
        bill_root = f"http://www.senate.mo.gov/{year2}info/BTS_Web/"
        index_url = f"{bill_root}BillList.aspx?SessionType={self.session_type(session)}"

        index_page = self.get(index_url).text
        index_page = lxml.html.fromstring(index_page)
        # Each bill is in it's own table (nested within a larger table).
        bill_tables = index_page.xpath("//a[@id]")

        if not bill_tables:
            return

        for bill_table in bill_tables:
            # Here we just search the whole table string to get the BillID that
            # the MO senate site uses.
            if re.search(r"dgBillList.*hlBillNum", bill_table.attrib["id"]):
                yield from self._parse_senate_billpage(
                    bill_root + bill_table.attrib.get("href"), session
                )

    def _scrape_lower_chamber(self, session):
        self.info("Scraping bills from lower chamber.")
        session_id = self._get_session_code(session)

        bill_list_content = self.get(
            f"https://documents.house.mo.gov/xml/{session_id}-BillList.xml"
        )
        bl_response = lxml.etree.fromstring(bill_list_content.content)

        for bill in bl_response.xpath("//BillXML"):
            bill_url = bill.xpath("./BillXMLLink/text()")[0]
            bill_type = bill.xpath("./BillType/text()")[0]
            bill_num = bill.xpath("./BillNumber/text()")[0]
            bill_year = bill.xpath("./SessionYear/text()")[0]
            bill_code = bill.xpath("./SessionCode/text()")[0]
            bill_id = f"{bill_type} {bill_num}"

            bill_content = self.get(bill_url)
            try:
                ib_response = lxml.etree.fromstring(bill_content.content)
            except lxml.etree.XMLSyntaxError:
                self.logger.error(
                    f"Error parsing XML for bill {bill_num} at {bill_url}"
                )
                continue

            yield from self.parse_house_bill(
                ib_response, bill_id, bill_year, bill_code, session
            )

    def parse_house_bill(self, response, bill_id, bill_year, bill_code, session):
        official_title = response.xpath("//BillInformation/CurrentBillString/text()")[0]
        try:
            bill_desc = response.xpath("//BillInformation/Title/LongTitle/text()")[0]
        except IndexError:
            bill_desc = "No title provided by the state website"
        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]
            bill_number = int(bill_id[3:].strip())
        else:
            bill_number = int(bill_id[3:])
        bid = bill_id.replace(" ", "")

        if bill_desc == "":
            if bill_number <= 20:
                # blank bill titles early in session are approp. bills
                bill_desc = "Appropriations Bill"
            else:
                self.logger.error(
                    "Blank title. Skipping. {} / {} / {}".format(
                        bill_id, bill_desc, official_title
                    )
                )
                return

        bill = Bill(
            identifier=bill_id,
            title=bill_desc,
            chamber="lower",
            legislative_session=session,
            classification=bill_type,
        )

        bill.add_title(official_title, note="official")
        bill_url = f"https://www.house.mo.gov/BillContent.aspx?bill={bid}&year={bill_year}&code={bill_code}&style=new"
        bill.add_source(bill_url)

        # add sponsors
        self.parse_house_sponsors(response, bill_id, bill)
        # add actions
        votes = self.parse_house_actions(response, bill)
        # yield if there are votes in the actions
        for vote in votes:
            yield vote
        # add bill versions
        self.parse_house_bill_versions(response, bill)
        # add bill subjects
        self.parse_house_bill_subjects(response, bill)

        yield bill

    def parse_house_sponsors(self, response, bill_id, bill):
        bill_sponsors = response.xpath("//BillInformation/Sponsor")
        for sponsor in bill_sponsors:
            sponsor_type = sponsor.xpath("./SponsorType/text()")[0]
            if sponsor_type == "Co-Sponsor":
                classification = "cosponsor"
                primary = False
            elif sponsor_type == "Sponsor":
                classification = "primary"
                primary = True
            elif sponsor_type == "HouseConferee" or sponsor_type == "SenateConferee":
                # these appear not to be actual sponsors of the bill but rather people who will
                # negotiate differing versions of the bill in a cross-chamber conference
                continue
            elif sponsor_type == "Handler":
                # slightly distinct from sponsor: The member who manages a bill on the floor of the House or Senate.
                # https://house.mo.gov/billtracking/info/glossary.htm
                # we decided to consider this a "cosponsor" relationship
                classification = "cosponsor"
                primary = False
            else:
                # didn't recognize sponsorship type, so we can't make this a sponsor
                # as classification is required (cannot be empty string)
                continue

            bill_sponsor = sponsor.xpath("./FullName/text()")[0]
            if bill_sponsor == "" and "HEC" in bill_id:
                bill.add_sponsorship(
                    "Petition", entity_type="", classification="primary", primary=True
                )
            else:
                bill.add_sponsorship(
                    bill_sponsor,
                    entity_type="person",
                    classification=classification,
                    primary=primary,
                )

    # Get the house bill actions and return the possible votes
    def parse_house_actions(self, response, bill):
        # add actions
        bill_actions = response.xpath("//BillInformation/Action")
        old_action_url = ""
        votes = []

        for action in bill_actions:
            action_url = (
                action.xpath("./Link/text()")[0]
                .replace(".aspx", "actions.aspx")
                .strip()
            )
            # the correct action description in the website is the combination of
            # Description, Comments, and RollCall
            # = Description - Comments - RollCall
            action_title = action.xpath("./Description/text()")[0]
            # if there is comments
            if action.xpath("./Comments"):
                action_comment = action.xpath("./Comments/text()")[0]
                action_title = f"{action_title} - {action_comment}"
            action_date = dt.datetime.strptime(
                action.xpath("./PubDate/text()")[0], "%Y-%m-%d"
            )
            actor = house_get_actor_from_action(action_title)
            type_class = self._get_action(actor, action_title)

            # if there is rollcall
            if action.xpath("./RollCall"):
                try:
                    rc_yes = action.xpath("./RollCall/TotalYes/text()")[0]
                except IndexError:
                    rc_yes = ""
                try:
                    rc_no = action.xpath("./RollCall/TotalNo/text()")[0]
                except IndexError:
                    rc_no = ""
                try:
                    rc_present = action.xpath("./RollCall/TotalPresent/text()")[0]
                except IndexError:
                    rc_present = ""
                action_title = f"{action_title} - AYES: {rc_yes} NOES: {rc_no} PRESENT: {rc_present}"

                vote = VoteEvent(
                    chamber=actor,
                    motion_text=action_title,
                    result="pass" if rc_yes > rc_no else "fail",
                    classification="passage",
                    start_date=TIMEZONE.localize(action_date),
                    bill=bill,
                )

                vote.add_source(action_url)
                votes.append(vote)

            bill.add_action(
                action_title,
                TIMEZONE.localize(action_date),
                chamber=actor,
                classification=type_class,
            )
            if old_action_url != action_url:
                bill.add_source(action_url)

            old_action_url = action_url

            # get journals (uncomments if this script needs)
            # journal_link = action.xpath('./JournalLink/text()').get()
            # if journal_link:
            #     house_journal_start = action.xpath(
            #         './HouseJournalStartPage/text()').get()
            #     senate_journal_start = action.xpath(
            #         './SenateJournalStartPage/text()').get()
            #     house_journal_end = action.xpath(
            #         './HouseJournalEndPage/text()').get()
            #     senate_journal_end = action.xpath(
            #         './SenateJournalEndPage/text()').get()
            #     version = ' - '.join(list(filter(None, [house_journal_start, house_journal_end]))) or ' - '.join(
            #         list(filter(None, [senate_journal_start, senate_journal_end])))
            #     if version:
            #         version = 'S' if senate_journal_start else 'H' + version
            #     else:
            #         version = "Missing description"
            #     if 'pdf' in journal_link:
            #         mimetype = "application/pdf"
            #     else:
            #         mimetype = "text/html"
            #     bill.add_version_link(
            #         version,
            #         journal_link,
            #         media_type=mimetype,
            #         on_duplicate="ignore",
            #     )
        return votes

    # Get the house bill versions
    def parse_house_bill_versions(self, response, bill):
        # house bill text
        for row in response.xpath("//BillInformation/BillText"):
            # some rows are just broken links, not real versions
            if row.xpath("./BillTextLink/text()"):
                version = row.xpath("./DocumentName/text()")[0]
                if not version:
                    version = "Missing description"
                path = row.xpath("./BillTextLink/text()")[0]
                if ".pdf" in path:
                    mimetype = "application/pdf"
                else:
                    mimetype = "text/html"
                bill.add_version_link(
                    version, path, media_type=mimetype, on_duplicate="ignore"
                )

        # house bill summaries
        for row in response.xpath("//BillInformation/BillSummary"):
            try:
                document = row.xpath("./DocumentName/text()")[0]
            except IndexError:
                # occasionally the xml element is just empty, ignore
                continue
            if document:
                path = row.xpath("./SummaryTextLink/text()")[0]
                summary_name = "Bill Summary ({})".format(document)
                if ".pdf" in path:
                    mimetype = "application/pdf"
                else:
                    mimetype = "text/html"
                bill.add_document_link(
                    summary_name, path, media_type=mimetype, on_duplicate="ignore"
                )

        # house bill amendments
        for row in response.xpath("//BillInformation/Amendment"):
            try:
                version = row.xpath("./AmendmentDescription/text()")[0]
            except IndexError:
                version = None
            path = row.xpath("./AmendmentText/text()")[0].strip()
            path_name = path.split("/")[-1].replace(".pdf", "")
            summary_name = f"Amendment {version or path_name}"

            status_desc = row.xpath("./StatusDescription/text()")[0]
            if status_desc:
                summary_name = f"{summary_name} ({status_desc})"

            if ".pdf" in path:
                mimetype = "application/pdf"
            else:
                mimetype = "text/html"
            bill.add_version_link(
                summary_name, path, media_type=mimetype, on_duplicate="ignore"
            )

        # house fiscal notes
        for row in response.xpath("//BillInformation/FiscalNote"):
            path = row.xpath("./FiscalNoteLink/text()")[0].strip()
            version = path.split("/")[-1].replace(".pdf", "")
            summary_name = f"Fiscal Note {version}"
            if ".pdf" in path:
                mimetype = "application/pdf"
            else:
                mimetype = ""
            bill.add_document_link(
                summary_name, path, media_type=mimetype, on_duplicate="ignore"
            )

        # house Witnesses
        for row in response.xpath("//BillInformation/Witness"):
            witness_elems = row.xpath("./WitnessFormsLink/text()")
            if not witness_elems or len(witness_elems) == 0:
                self.logger.warning(
                    f"Found missing Witness Form link for bill {bill.identifier}"
                )
                continue
            path = witness_elems[0].strip()
            summary_name = "Bill Summary (Witnesses)"
            if ".pdf" in path:
                mimetype = "application/pdf"
            else:
                mimetype = ""
            bill.add_document_link(
                summary_name, path, media_type=mimetype, on_duplicate="ignore"
            )

    def parse_house_bill_subjects(self, response, bill):
        for row in response.xpath("//BillInformation/SubjectIndex"):
            subject = row.xpath("./SubjectName/text()")[0]
            if not subject:
                subject = "Missing subject"
            bill.add_subject(subject)

    def scrape(self, chamber=None, session=None):
        # special sessions and other year manipulation messes up the session variable
        # but we need it for correct output
        self._session_id = session

        if chamber in ["upper", None]:
            self._scrape_senate_subjects(session)
            yield from self._scrape_upper_chamber(session)
        if chamber in ["lower", None]:
            yield from self._scrape_lower_chamber(session)

        if len(self._bad_urls) > 0:
            self.warning("WARNINGS:")
            for url in self._bad_urls:
                self.warning("{}".format(url))
