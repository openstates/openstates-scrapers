import datetime
import re

import lxml.etree

from openstates.scrape import Bill, Scraper
from utils import LXMLMixin

# Skip Amendment for now, data is included in Bill entry
_scrapable_types = ["Bill", "Bill&Amend", "CMZ Permit", "Other", "Resolution"]

_action_pairs = (
    ("ContentPlaceHolder_DateIntroLabel", "Introduced", "introduction"),
    ("ContentPlaceHolder_DateRecLabel", "Received", "filing"),
    ("ContentPlaceHolder_DateAssignLabel", "Assigned", ""),
    ("ContentPlaceHolder_DateToSenLabel", "Sent to Senator", ""),
    (
        "ContentPlaceHolder_DateToGovLabel",
        "Sent to Governor",
        "executive-receipt",
    ),
    (
        "ContentPlaceHolder_DateAppGovLabel",
        "Signed by Governor",
        "executive-signature",
    ),
    ("ContentPlaceHolder_DateVetoedLabel", "Vetoed", "executive-veto"),
    (
        "ContentPlaceHolder_DateOverLabel",
        "Governor Veto Overridden",
        "veto-override-passage",
    ),
)

_action_ids = (
    ("ContentPlaceHolder_ComActionLabel", "upper"),
    ("ContentPlaceHolder_FloorActionLabel", "upper"),
    ("ContentPlaceHolder_RulesActionLabel", "upper"),
    ("ContentPlaceHolder_RemarksLabel", "executive"),
)

_action_re = (
    ("AMENDED AND REPORTED", ["referral-committee", "amendment-passage"]),
    ("REPORTED OUT", "referral-committee"),
    ("ADOPTED", "passage"),
    ("HELD IN COMMITTEE", ""),
    ("AMENDED", "amendment-passage"),
)

_committees = (
    ("COCHPY&R", "COMMITTEE OF CULTURE, HISTORIC PRESERVATION, YOUTH & RECREATION"),
    ("COEDA&P", "COMMITTEE OF ECONOMIC DEVELOPMENT, AGRICULTURE & PLANNING"),
    ("COE&WD", "COMMITTEE OF EDUCATION & WORKFORCE DEVELOPMENT"),
    ("HEALTH", "COMMITTEE OF ENERGY & ENVIRONMENTAL PROTECTION"),
    ("COF", "COMMITTEE OF FINANCE"),
    ("COHHHS&VA", "COMMITTEE OF HEALTH, HOSPITAL & HUMAN SERVICES"),
    ("COHSJ&PS", "COMMITTEE OF HOMELAND SECURITY, PUBLIC SAFETY & JUSTICE"),
    ("PUBLICWRKS", "COMMITTEE OF HOUSING, PUBLIC WORKS & WASTE MANAGEMENT"),
    ("RULJUD", "COMMITTEE OF RULES & JUDICIARY"),
    ("WHOLE", "COMMITTEE OF THE WHOLE"),
    ("GOVSERV", "COMMITTEE ON GOVERNMENT SERVICES, CONSUMER AND VETERANS AFFAIRS"),
    ("COGS&H", "COMMITTEE ON GOVERNMENT SERVICES, CONSUMER AND VETERANS AFFAIRS"),
    ("", "Legislative Youth Advisory Counsel"),
    ("ZONING", "ZONING"),
)


class VIBillScraper(Scraper, LXMLMixin):
    session = ""
    committees = []

    def scrape(self, session=None, chambers=None):
        self.session = session

        if chambers is None:
            chambers = ["upper", "lower"]

        # First we get the Form to get our ASP viewstate variables
        search_url = "https://legvi.org/billtracking/default.aspx"
        doc = lxml.html.fromstring(self.get(url=search_url, verify=False).text)

        (viewstate,) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = doc.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = doc.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        # (previouspage,) = doc.xpath('//input[@id="__PREVIOUSPAGE"]/@value')

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            # "__PREVIOUSPAGE": previouspage,
            "__EVENTTARGET": "ctl00$ContentPlaceHolder$leginum",
            "ctl00$ContentPlaceHolder$leginum": session,
            "ctl00$ContentPlaceHolder$sponsor": "",
            "ctl00$ContentPlaceHolder$billnumber": "",
            "ctl00$ContentPlaceHolder$actnumber": "",
            "ctl00$ContentPlaceHolder$subject": "",
            "ctl00$ContentPlaceHolder$BRNumber": "",
            "ctl00$ContentPlaceHolder$ResolutionNumber": "",
            "ctl00$ContentPlaceHolder$AmendmentNumber": "",
            "ctl00$ContentPlaceHolder$GovernorsNumber": "",
        }

        # Then we post the to the search form once to set our ASP viewstate
        form = self.post(url=search_url, data=form, allow_redirects=True)
        doc = lxml.html.fromstring(form.text)

        (viewstate,) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = doc.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = doc.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        # (previouspage,) = doc.xpath('//input[@id="__PREVIOUSPAGE"]/@value')

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            # "__PREVIOUSPAGE": previouspage,
            "__EVENTTARGET": "ctl00$ContentPlaceHolder$Button1",
            "ctl00$ContentPlaceHolder$leginum": session,
            "ctl00$ContentPlaceHolder$sponsor": "",
            "ctl00$ContentPlaceHolder$billnumber": "",
            "ctl00$ContentPlaceHolder$actnumber": "",
            "ctl00$ContentPlaceHolder$subject": "",
            "ctl00$ContentPlaceHolder$BRNumber": "",
            "ctl00$ContentPlaceHolder$ResolutionNumber": "",
            "ctl00$ContentPlaceHolder$AmendmentNumber": "",
            "ctl00$ContentPlaceHolder$GovernorsNumber": "",
        }
        # Then we submit to the results url to actually get the bill list
        results_url = "https://legvi.org/billtracking/Default.aspx"
        bills_list = self.post(url=results_url, data=form, allow_redirects=True)
        bills_list = lxml.html.fromstring(bills_list.text)

        bills_list.make_links_absolute("https://legvi.org/billtracking/")
        bills = bills_list.xpath('//table[@id="ContentPlaceHolder_BillsDataGrid"]/tr')

        for bill_row in bills[1:]:
            (bill_type,) = bill_row.xpath("./td[6]/font/text()")

            if bill_type in _scrapable_types:
                (landing_page,) = bill_row.xpath(".//td/font/a/@href")
                yield from self.scrape_bill(landing_page)

    def scrape_bill(self, bill_page_url):
        bill_page = lxml.html.fromstring(self.get(bill_page_url, verify=False).text)

        title = bill_page.xpath('//span[@id="ContentPlaceHolder_SubjectLabel"]/text()')
        if title:
            title = title[0]
        else:
            self.warning("Missing bill title {}".format(bill_page_url))
            return False

        bill_no = bill_page.xpath(
            '//span[@id="ContentPlaceHolder_BillNumberLabel"]/a/text()'
        )
        if bill_no:
            bill_no = bill_no[0]
        else:
            bill_no = bill_page.xpath(
                '//span[@id="ContentPlaceHolder_BillNumberLabel"]/text()'
            )
            if bill_no:
                bill_no = bill_no[0]
            else:
                self.error("Missing bill number {}".format(bill_page_url))
                return False

        bill = Bill(
            bill_no,
            legislative_session=self.session,
            chamber="legislature",
            title=title,
            classification="bill",
        )

        bill.add_source(bill_page_url)

        self.parse_versions(bill, bill_page, bill_no)
        self.parse_acts(bill, bill_page)

        sponsors = bill_page.xpath(
            '//span[@id="ContentPlaceHolder_SponsorsLabel"]/text()'
        )
        if sponsors:
            self.assign_sponsors(bill, sponsors[0], "primary")

        cosponsors = bill_page.xpath(
            '//span[@id="ContentPlaceHolder_CoSponsorsLabel"]/text()'
        )
        if cosponsors:
            self.assign_sponsors(bill, cosponsors[0], "cosponsor")

        self.parse_date_actions(bill, bill_page)
        self.parse_actions(bill, bill_page)

        v_url = f"https://billtracking.legvi.org:8082/preview/Bill%2F{bill_no}"
        bill.add_version_link(
            bill_no,
            v_url,
            media_type="application/pdf",
            on_duplicate="ignore",
        )

        yield bill

    def parse_versions(self, bill, bill_page, bill_no):
        bill_version = bill_page.xpath(
            '//span[@id="ContentPlaceHolder_BillNumberLabel"]/a/@href'
        )
        if bill_version:
            bill.add_version_link(
                note=bill_no,
                url="https://legvi.org/billtracking/{}".format(bill_version[0]),
                media_type="application/pdf",
            )

    def parse_acts(self, bill, bill_page):
        bill_act = bill_page.xpath('//span[@id="ContentPlaceHolder_ActNumberLabel"]/a')
        if bill_act:
            (act_title,) = bill_act[0].xpath("./text()")
            act_title = "Act {}".format(act_title)
            (act_link,) = bill_act[0].xpath("./@href")
            act_link = "https://legvi.org/billtracking/{}".format(act_link)
            bill.add_document_link(
                note=act_title, url=act_link, media_type="application/pdf"
            )

    def clean_names(self, name_str):
        # Clean up the names a bit to allow for comma splitting
        name_str = re.sub(", Jr", " Jr.", name_str, flags=re.I)
        name_str = re.sub(", Sr", " Sr.", name_str, flags=re.I)
        return name_str

    def assign_sponsors(self, bill, sponsors, sponsor_type):
        sponsors = self.clean_names(sponsors)
        sponsors = sponsors.split(", ")
        for sponsor in sponsors:
            if sponsor.strip() == "":
                continue
            bill.add_sponsorship(
                classification=sponsor_type,
                name=sponsor.strip(),
                entity_type="person",
                primary=(True if sponsor_type == "sponsor" else False),
                # on_duplicate="ignore",
            )

    def parse_date_actions(self, bill, bill_page):
        # There's a set of dates on the bill page denoting specific actions
        # These are mapped in _action_pairs above
        for xpath, action_name, action_type in _action_pairs:
            action_date = bill_page.xpath('//span[@id="{}"]/text()'.format(xpath))
            if action_date:
                bill.add_action(
                    description=action_name,
                    date=self.parse_date(action_date[0]),
                    chamber="legislature",
                    classification=action_type,
                )

    def parse_date(self, date_str):
        # manual typo fix
        date_str = date_str.replace("07/21/5", "07/21/15")
        try:
            return datetime.datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            return datetime.datetime.strptime(date_str, "%m/%d/%y").date()

    def parse_actions(self, bill, bill_page):
        # Aside from the actions implied by dates, which are handled in parse_date_actions
        # Each actor has 1+ fields for their actions,
        # Pull (DATE, Action) pairs out of text, and categorize the action
        for xpath, actor in _action_ids:
            actions = bill_page.xpath('//span[@id="{}"]/text()'.format(xpath))
            if actions:
                for action_date, action_text in self.split_action(actions[0]):
                    try:
                        bill.add_action(
                            description=action_text,
                            chamber=actor,
                            date=self.parse_date(action_date),
                            classification=self.categorize_action(action_text),
                        )
                    except ValueError:
                        self.warning(
                            f"Unable to parse time from {action_date}, skipping"
                        )
                        continue

    def split_action(self, action_str):
        # Turns 01/01/2015 ACTION1 02/02/2016 ACTION2
        # Into (('01/01/2015', 'ACTION NAME'),('02/02/2016', 'ACTION2'))
        actions = re.split(r"(\d{1,2}/\d{1,2}/\d{1,2})", action_str)
        # Trim out whitespace and leading/trailing dashes
        actions = [re.sub(r"^-\s+|^-|-$", "", action.strip()) for action in actions]
        # Trim out empty list items from re.split
        actions = list(filter(None, actions))
        return self.grouped(actions, 2)

    def categorize_action(self, action):
        for pattern, types in _action_re:
            if re.findall(pattern, action, re.IGNORECASE):
                return types
        return ""

    def grouped(self, iterable, n):
        # Return a list grouped by n
        # "s -> (s1,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
        return zip(*[iter(iterable)] * n)
