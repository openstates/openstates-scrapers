import re
import datetime
import scrapelib
import pytz
from collections import defaultdict

from .actions import Categorizer
from .utils import xpath
from openstates.scrape import Scraper, Bill, VoteEvent as Vote
from utils import LXMLMixin

import lxml.etree
import lxml.html
import feedparser


class WABillScraper(Scraper, LXMLMixin):
    # API Docs: http://wslwebservices.leg.wa.gov/legislationservice.asmx

    _base_url = "http://wslwebservices.leg.wa.gov/legislationservice.asmx"
    categorizer = Categorizer()
    _subjects = defaultdict(list)

    _chamber_map = {"House": "lower", "Senate": "upper", "Joint": "joint"}

    _bill_id_list = []
    versions = {}

    _TZ = pytz.timezone("US/Eastern")

    ORDINALS = {
        "2": "Second",
        "3": "Third",
        "4": "Fourth",
        "5": "Fifth",
        "6": "Sixth",
        "7": "Seventh",
        "8": "Eighth",
        "9": "Ninth",
        "": "",
    }

    def build_subject_mapping(self, year):
        url = "http://apps.leg.wa.gov/billsbytopic/Results.aspx?year=%s" % year
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute("http://apps.leg.wa.gov/billsbytopic/")
        for link in doc.xpath('//a[contains(@href, "ResultsRss")]/@href'):
            subject = link.rsplit("=", 1)[-1]
            link = link.replace(" ", "%20")

            # Strip invalid characters
            rss = re.sub(r"^[^<]+", "", self.get(link).text)
            rss = feedparser.parse(rss)
            for e in rss["entries"]:
                match = re.match(r"\w\w \d{4}", e["title"])
                if match:
                    self._subjects[match.group()].append(subject)

    def _load_versions(self, chamber):
        base_url = "http://lawfilesext.leg.wa.gov/Biennium/{}/Htm/Bills/".format(
            self.biennium
        )
        bill_types = {
            "Bills": "B",
            "Resolutions": "R",
            "Concurrent Resolutions": "CR",
            "Joint Memorials": "JM",
            "Joint Resolutions": "JR",
        }
        chamber = {"lower": "House", "upper": "Senate"}[chamber]

        for bill_type in bill_types:
            try:
                doc = self.lxmlize(base_url + chamber + " " + bill_type)
            except scrapelib.HTTPError:
                return
            documents = doc.xpath("//a")[1:]
            for document in documents:
                (link,) = document.xpath("@href")
                (text,) = document.xpath("text()")
                (
                    bill_num,
                    is_substitute,
                    substitute_num,
                    is_engrossed,
                    engrossed_num,
                ) = re.search(
                    r"""(?x)
                    ^(\d+)  # Bill number
                    (-S(\d)?)?  # Substitution indicator
                    (\.E(\d)?)?  # Engrossment indicator
                    \s?(?:.*?)  # Document name, only for some types
                    \.htm$""",
                    text,
                ).groups()

                bill_id = chamber[0] + bill_types[bill_type] + " " + bill_num

                name = bill_type[:-1]
                if is_substitute:
                    name = "Substitute " + name
                    if substitute_num:
                        name = " ".join([self.ORDINALS[substitute_num], name])
                if is_engrossed:
                    name = "Engrossed " + name
                    if engrossed_num:
                        name = " ".join([self.ORDINALS[engrossed_num], name])

                if not self.versions.get(bill_id):
                    self.versions[bill_id] = []
                self.versions[bill_id].append(
                    {"note": name, "url": link, "media_type": "text/html"}
                )

    def _load_documents(self, chamber):
        chamber = {"lower": "House", "upper": "Senate"}[chamber]
        self.documents = {}

        document_types = ["Amendments", "Bill Reports", "Digests"]
        for document_type in document_types:
            url = "http://lawfilesext.leg.wa.gov/Biennium/{0}" "/Htm/{1}/{2}/".format(
                self.biennium, document_type, chamber
            )

            try:
                doc = self.lxmlize(url)
            except scrapelib.HTTPError:
                return

            documents = doc.xpath("//a")[1:]
            for document in documents:

                (link,) = document.xpath("@href")
                (text,) = document.xpath("text()")

                (
                    bill_number,
                    is_substitute,
                    substitute_num,
                    is_engrossed,
                    engrossed_num,
                    document_title,
                ) = re.search(
                    r"""(?x)
                    (?:[[A-Z]+]){0,1} # Occasional doc doesnt start with number
                    (\d+)  # Bill number
                    (-S(\d)?)?  # Substitution indicator
                    (\.E(\d)?)?  # Engrossment indicator
                    \s?(.*?)  # Document name
                    \.htm$""",
                    text,
                ).groups()

                if document_type == "Amendments":
                    name = "Amendment {}".format(document_title[4:])

                elif document_type == "Bill Reports":
                    name = " ".join(
                        [
                            x
                            for x in [
                                "Report",
                                "for" if (is_substitute or is_engrossed) else "",
                                self.ORDINALS[engrossed_num] if engrossed_num else "",
                                "Engrossed" if is_engrossed else "",
                                self.ORDINALS[substitute_num] if substitute_num else "",
                                "Substitute" if is_substitute else "",
                            ]
                            if x.strip()
                        ]
                    )

                elif document_type == "Digests":
                    name = "Digest"
                    if is_substitute:
                        name = "Digest for Substitute"
                        if substitute_num:
                            name = "Digest for {} Substitute".format(
                                self.ORDINALS[substitute_num]
                            )

                if not self.documents.get(bill_number):
                    self.documents[bill_number] = []
                self.documents[bill_number].append(
                    {"note": name, "url": link, "media_type": "text/html"}
                )

    def get_prefiles(self, chamber, session, year):
        url = "http://apps.leg.wa.gov/billinfo/prefiled.aspx?year={}".format(year)
        page = self.lxmlize(url)

        bill_rows = page.xpath('//table[@id="ctl00_ContentPlaceHolder1_gvPrefiled"]/tr')
        for row in bill_rows[1:]:
            if row.xpath("td[1]/a"):
                bill_id = row.xpath("td[1]/a/text()")[0]
                self._bill_id_list.append(bill_id)

        return self._bill_id_list

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber else ["upper", "lower"]

        year = int(session[0:4])

        self._bill_id_list = self.get_prefiles(chamber, session, year)

        for chamber in chambers:
            self.scrape_chamber(chamber, session)

        # de-dup bill_id
        for bill_id in list(set(self._bill_id_list)):
            yield from self.scrape_bill(chamber, session, bill_id)

    def scrape_chamber(self, chamber, session):
        self.biennium = "%s-%s" % (session[0:4], session[7:9])
        self._load_versions(chamber)
        self._load_documents(chamber)

        # to test a specific bill...
        # yield from self.scrape_bill('lower', '2019-2020', 'HB 2217')

        year = int(session[0:4])

        # first go through API response and get bill list
        max_year = year if int(datetime.date.today().year) < year + 1 else year + 1
        for y in (year, max_year):
            self.build_subject_mapping(y)
            url = "%s/GetLegislationByYear?year=%s" % (self._base_url, y)

            try:
                page = self.get(url)
            except scrapelib.HTTPError:
                continue  # future years.

            page = lxml.etree.fromstring(page.content)
            for leg_info in xpath(page, "//wa:LegislationInfo"):
                bill_id = xpath(leg_info, "string(wa:BillId)")
                bill_num = xpath(leg_info, "number(wa:BillNumber)")
                bill_chamber = xpath(leg_info, "string(wa:OriginalAgency)")
                bill_chamber = self._chamber_map[bill_chamber]

                # Skip gubernatorial appointments
                if bill_num >= 9000:
                    continue
                # skip ballot initiatives
                if bill_id.startswith("SI") or bill_id.startswith("HI"):
                    continue

                if bill_chamber != chamber:
                    continue

                # normalize bill_id
                bill_id_norm = re.findall(r"(?:S|H)(?:B|CR|JM|JR|R) \d+", bill_id)
                if not bill_id_norm:
                    self.warning("illegal bill_id %s" % bill_id)
                    continue

                self._bill_id_list.append(bill_id_norm[0])

    def scrape_bill(self, chamber, session, bill_id):
        bill_num = bill_id.split()[1]

        url = "%s/GetLegislation?biennium=%s&billNumber" "=%s" % (
            self._base_url,
            self.biennium,
            bill_num,
        )

        page = self.get(url)
        page = lxml.etree.fromstring(page.content)
        page = xpath(page, "//wa:Legislation")[0]

        xml_chamber = xpath(page, "string(wa:OriginalAgency)")
        chamber = self._chamber_map[xml_chamber]

        title = xpath(page, "string(wa:LongDescription)")

        bill_type = xpath(
            page, "string(wa:ShortLegislationType/wa:LongLegislationType)"
        )
        bill_type = bill_type.lower()

        if bill_type == "gubernatorial appointment":
            return

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=[bill_type],
        )
        fake_source = (
            "http://apps.leg.wa.gov/billinfo/"
            "summary.aspx?bill=%s&year=%s" % (bill_num, session[0:4])
        )

        bill.add_source(fake_source)

        try:
            for version in self.versions[bill_id]:
                bill.add_version_link(
                    note=version["note"],
                    url=version["url"],
                    media_type=version["media_type"],
                )
        except KeyError:
            self.warning("No versions were found for {}".format(bill_id))

        try:
            for document in self.documents[bill_num]:
                bill.add_document_link(
                    note=document["note"],
                    url=document["url"],
                    media_type=document["media_type"],
                )
        except KeyError:
            pass

        self.scrape_sponsors(bill)
        self.scrape_actions(bill, bill_num)
        self.scrape_hearings(bill, bill_num)
        yield from self.scrape_votes(bill)
        bill.subject = list(set(self._subjects[bill_id]))
        yield bill

    def scrape_sponsors(self, bill):
        bill_id = bill.identifier.replace(" ", "%20")

        url = "%s/GetSponsors?biennium=%s&billId=%s" % (
            self._base_url,
            self.biennium,
            bill_id,
        )

        page = self.get(url)
        page = lxml.etree.fromstring(page.content)

        first = True
        for sponsor in xpath(page, "//wa:Sponsor/wa:Name"):
            name = sponsor.text
            spon_type = "primary" if first else "cosponsor"
            bill.add_sponsorship(
                name,
                classification=spon_type,
                entity_type="person",
                primary=spon_type == "primary",
            )
            first = False

    def scrape_hearings(self, bill, bill_num):
        # http://wslwebservices.leg.wa.gov/LegislationService.asmx?op=GetHearings&
        # biennium=2019-20&billNumber=5000
        url = (
            "http://wslwebservices.leg.wa.gov/LegislationService.asmx/GetHearings"
            "?biennium={}&billNumber={}".format(self.biennium, bill_num)
        )
        try:
            page = self.get(url)
        except scrapelib.HTTPError as e:
            self.warning(e)
            return

        page = lxml.etree.fromstring(page.content)
        for hearing in xpath(page, "//wa:Hearing"):
            action_date = xpath(hearing, "string(wa:CommitteeMeeting/wa:Date)")
            action_date = datetime.datetime.strptime(action_date, "%Y-%m-%dT%H:%M:%S")

            # build the time before we convert to utc
            action_time = action_date.strftime("%I:%M %p")

            action_date = self._TZ.localize(action_date)
            action_actor_str = xpath(hearing, "string(wa:CommitteeMeeting/wa:Agency)")
            action_actor = "upper" if action_actor_str == "Senate" else "lower"

            committee_name = xpath(
                hearing,
                "string(wa:CommitteeMeeting/wa:Committees/" "wa:Committee/wa:Name)",
            )

            # Scheduled for public hearing in the Senate Committee on Law & Justice
            # at 10:00 AM (Subject to change). (Committee Materials)
            action_name = (
                "Scheduled for public hearing in the {}"
                " Committee on {} at {}".format(
                    action_actor_str, committee_name, action_time
                )
            )
            bill.add_action(action_name, action_date, chamber=action_actor)

    def scrape_actions(self, bill, bill_num):
        session = bill.legislative_session
        # chamber = bill['chamber']

        # GetLegislativeStatusChangesByBillNumber gives full results,
        # unlike GetLegislativeStatusChangesByBillId
        # http://wslwebservices.leg.wa.gov/legislationservice.asmx/GetLegislativeStatusChangesByBillNumber?
        # biennium=2015-16&billNumber=1002&beginDate=2014-01-01&endDate=2018-12-31&chamber=senate
        # biennium=2019-20&billNumber=5121&beginDate=2019-01-01&endDate=2019-12-31&chamber=house

        # Set the start date back a year to catch prefile / intro actions
        start_date = datetime.date(int(session[0:4]) - 1, 1, 1)
        end_date = datetime.date(int(session[0:4]) + 1, 12, 31)

        url = (
            "http://wslwebservices.leg.wa.gov/legislationservice.asmx/"
            "GetLegislativeStatusChangesByBillNumber?biennium={}&billNumber={}"
            "&beginDate={}&endDate={}".format(
                self.biennium, bill_num, start_date, end_date
            )
        )
        try:
            page = self.get(url)
        except scrapelib.HTTPError as e:
            self.warning(e)
            return

        page = lxml.etree.fromstring(page.content)

        for action in xpath(page, "//wa:LegislativeStatus"):
            action_name = xpath(action, "string(wa:HistoryLine)")

            action_date = xpath(action, "string(wa:ActionDate)")
            action_date = datetime.datetime.strptime(
                action_date, "%Y-%m-%dT%H:%M:%S"
            ).strftime("%Y-%m-%d")

            bill_id = xpath(action, "string(wa:BillId)")

            if "S" in bill_id:
                if (
                    "Governor" in bill_id
                    or "Laws" in bill_id
                    or "Effective date" in bill_id
                ):
                    actor = "executive"
                else:
                    actor = "upper"
            elif "H" in bill_id:
                actor = "lower"
            temp = self.categorizer.categorize(action_name)
            classification = temp["classification"]
            try:
                committees = temp["committees"]
            except KeyError:
                committees = []
            related_entities = []
            for committee in committees:
                related_entities.append({"type": "committee", "name": committee})

            bill.add_action(
                description=action_name,
                date=action_date,
                chamber=actor,
                classification=classification,
                related_entities=related_entities,
            )

    def scrape_votes(self, bill):
        bill_num = bill.identifier.split()[1]

        url = (
            "http://wslwebservices.leg.wa.gov/legislationservice.asmx/"
            "GetRollCalls?billNumber=%s&biennium=%s" % (bill_num, self.biennium)
        )
        page = self.get(url)
        page = lxml.etree.fromstring(page.content)

        for rc in xpath(page, "//wa:RollCall"):
            motion = xpath(rc, "string(wa:Motion)")
            seq_no = xpath(rc, "string(wa:SequenceNumber)")

            date = xpath(rc, "string(wa:VoteDate)").split("T")[0]
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

            yes_count = int(xpath(rc, "string(wa:YeaVotes/wa:Count)"))
            no_count = int(xpath(rc, "string(wa:NayVotes/wa:Count)"))
            abs_count = int(xpath(rc, "string(wa:AbsentVotes/wa:Count)"))
            ex_count = int(xpath(rc, "string(wa:ExcusedVotes/wa:Count)"))

            other_count = abs_count + ex_count

            agency = xpath(rc, "string(wa:Agency)")
            chamber = {"House": "lower", "Senate": "upper"}[agency]

            vote = Vote(
                chamber=chamber,
                start_date=date,
                motion_text="{} (#{})".format(motion, seq_no),
                result="pass" if yes_count > (no_count + other_count) else "fail",
                bill=bill,
                classification=[],
            )
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("other", other_count)
            vote.add_source(url)
            for sv in xpath(rc, "wa:Votes/wa:Vote"):
                name = xpath(sv, "string(wa:Name)")
                vtype = xpath(sv, "string(wa:VOte)")

                if vtype == "Yea":
                    vote.yes(name)
                elif vtype == "Nay":
                    vote.no(name)
                else:
                    vote.vote("other", name)

            yield vote
