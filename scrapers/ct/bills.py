import re
import datetime
import string
import urllib3

import types  # fmt: skip  # noqa: F401

from collections import defaultdict
from operator import itemgetter

import lxml.html

from openstates.scrape import Scraper, Bill
from .utils import parse_directory_listing, open_csv
from .actions import Categorizer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SkipBill(Exception):
    pass


class CTBillScraper(Scraper):
    latest_only = True
    categorizer = Categorizer()
    action_list = {}

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        self.bills = defaultdict(list)
        self._committee_names = {}
        self._subjects = defaultdict(list)
        self.scrape_committee_names()
        self.scrape_subjects()
        self.scrape_bill_history()

        yield from self.scrape_bill_info(session, chambers)

    def scrape_bill_info(self, session, chambers):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        data = self.get(info_url)
        page = open_csv(data)

        # # For local dev -- bill_info.csv can get to mulitple megabytes and CT's
        # # ftp server is not super fast, so uncomment this to use a local copy.
        # info_url = "https://ct.gov"
        # with open('ct.csv', 'rb') as file:
        #     file_content = file.read()
        #     test = types.SimpleNamespace()
        #     test.content = file_content
        #     page = open_csv(test)

        chamber_map = {"H": "lower", "S": "upper"}

        for row in page:
            if row["sess_year"] != session:
                continue
            bill_id = row["bill_num"]
            chamber = chamber_map[bill_id[0]]

            if chamber not in chambers:
                continue

            if re.match(r"^(S|H)J", bill_id):
                bill_type = "joint resolution"
            elif re.match(r"^(S|H)R", bill_id):
                bill_type = "resolution"
            else:
                bill_type = "bill"

            bill = Bill(
                identifier=bill_id,
                legislative_session=session,
                title=row["bill_title"],
                classification=bill_type,
                chamber=chamber,
            )
            bill.add_source(info_url)
            self.scrape_actions(bill, chamber)
            try:
                for subject in self._subjects[bill_id]:
                    bill.subject.append(subject)

                self.bills[bill_id] = [bill, chamber]
                yield from self.scrape_bill_page(bill)
            except SkipBill:
                self.warning("no such bill: " + bill_id)
                pass

    def scrape_bill_page(self, bill):
        # Removes leading zeroes in the bill number.
        bill_number = "".join(re.split("0+", bill.identifier, 1))

        url = (
            "https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill"
            "&bill_num=%s&which_year=%s" % (bill_number, bill.legislative_session)
        )

        page = self.get(url, verify=False).text
        if "not found in Database" in page:
            raise SkipBill()
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill.add_source(url)

        spon_type = "primary"

        for sponsor in page.xpath('//a[contains(@href,"CGAMemberBills.asp")]/text()'):
            sponsor = str(sponsor.strip())
            if sponsor:
                sponsor = string.capwords(
                    sponsor.replace("Rep. ", "").replace("Sen. ", "")
                )
                sponsor = sponsor.split(",")[0]
                bill.add_sponsorship(
                    name=sponsor,
                    classification=spon_type,
                    entity_type="person",
                    primary=spon_type == "primary",
                )
        for link in page.xpath("//a[contains(@href, '/FN/')]"):
            bill.add_document_link(link.text.strip(), link.attrib["href"])

        for link in page.xpath("//a[contains(@href, '/BA/')]"):
            bill.add_document_link(link.text.strip(), link.attrib["href"])

        for link in page.xpath(
            "//a[(contains(@href, '/pdf/') or contains(@href, '/PDF/')) and "
            "(contains(@href, '/TOB/') or contains(@href, '/FC/') or contains(@href, '/ACT/'))]"
        ):
            bill.add_version_link(
                link.text.strip(), link.attrib["href"], media_type="application/pdf"
            )

        yield bill

    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = self.get(history_url)
        page = open_csv(page)

        for row in page:
            bill_id = row["bill_num"]
            if bill_id not in self.action_list:
                self.action_list[bill_id] = []
            self.action_list[bill_id].append(row)

    def scrape_actions(self, bill: Bill, initial_chamber: str):

        actions = self.action_list[bill.identifier]
        actions.sort(key=itemgetter("act_date"))
        act_chamber = initial_chamber

        for row in actions:
            date = row["act_date"]
            date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date()

            action = row["act_desc"].strip()
            act_type = []

            match = re.search(r"COMM(ITTEE|\.) ON$", action)
            if match:
                comm_code = row["qual1"]
                comm_name = self._committee_names.get(comm_code, comm_code)
                action = "%s %s" % (action, comm_name)
                act_type.append("referral-committee")
            elif row["qual1"]:
                if bill.legislative_session in row["qual1"]:
                    action += " (%s" % row["qual1"]
                    if row["qual2"]:
                        action += " %s)" % row["qual2"]
                else:
                    action += " %s" % row["qual1"]

            match = re.search(r"REFERRED TO OLR, OFA (.*)", action)
            if match:
                action = (
                    "REFERRED TO Office of Legislative Research"
                    " AND Office of Fiscal Analysis %s" % (match.group(1))
                )

            action_attr = self.categorizer.categorize(action)
            classification = action_attr["classification"]

            bill.add_action(
                description=action,
                date=date,
                chamber=act_chamber,
                classification=classification,
            )

            # if an action is the terminal step in one chamber,
            # switch the chamber for the next action
            if (
                "TRANS.TO HOUSE" in action
                or "SENATE PASSED" in action
                or "SEN. PASSED" in action
            ):
                act_chamber = "lower"

            if "TRANSMITTED TO SENATE" in action or "HOUSE PASSED" in action:
                act_chamber = "upper"

    def scrape_versions(self, chamber, session):
        chamber_letter = {"upper": "s", "lower": "h"}[chamber]
        versions_url = "ftp://ftp.cga.ct.gov/%s/tob/%s/pdf/" % (session, chamber_letter)

        page = self.get(versions_url).text
        files = parse_directory_listing(page)

        for f in files:
            match = re.match(r"^\d{4,4}([A-Z]+-\d{5,5})-(R\d\d)", f.filename)
            if not match:
                self.warning("bad version filename %s", f.filename)
                continue
            bill_id = match.group(1).replace("-", "")

            try:
                bill = self.bills[bill_id][0]
            except IndexError:
                continue

            url = versions_url + f.filename
            bill.add_version_link(
                media_type="application/pdf", url=url, note=match.group(2)
            )

    def scrape_subjects(self):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/subject.csv"
        data = self.get(info_url)
        page = open_csv(data)

        for row in page:
            self._subjects[row["bill_num"]].append(row["subj_desc"])

    def scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(comm_url)
        page = open_csv(page)

        for row in page:
            comm_code = row["comm_code"].strip()
            comm_name = row["comm_name"].strip()
            comm_name = re.sub(r" Committee$", "", comm_name)
            self._committee_names[comm_code] = comm_name
