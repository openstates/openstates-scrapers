import datetime
import ftplib
import re
import time
from urllib import parse as urlparse
import xml.etree.cElementTree as etree

from openstates.scrape import Scraper, Bill
from openstates.scrape.base import ScrapeError
from utils import LXMLMixin


class TXBillScraper(Scraper, LXMLMixin):
    _FTP_ROOT = "ftp.legis.state.tx.us"
    CHAMBERS = {"H": "lower", "S": "upper"}
    NAME_SLUGS = {
        "I": "Introduced",
        "E": "Engrossed",
        "S": "Senate Committee Report",
        "H": "House Committee Report",
        "F": "Enrolled",
    }
    companion_url = (
        "https://capitol.texas.gov/BillLookup/Companions.aspx" "?LegSess={}&Bill={}"
    )

    def _get_ftp_files(self, root, dir_):
        """ Recursively traverse an FTP directory, returning all files """

        for i in range(3):
            try:
                ftp = ftplib.FTP(root)
                break
            except (EOFError, ftplib.error_temp):
                time.sleep(2 ** i)
        else:
            raise
        ftp.login()
        ftp.cwd("/" + dir_)
        self.info("Searching an FTP folder for files ({})".format(dir_))

        lines = []
        ftp.retrlines("LIST", lines.append)
        for line in lines:
            (_date, _time, is_dir, _file_size, name) = re.search(
                r"""(?x)
                    ^(\d{2}-\d{2}-\d{2})\s+  # Date in mm-dd-yy
                    (\d{2}:\d{2}[AP]M)\s+  # Time in hh:mmAM/PM
                    (<DIR>)?\s+  # Directories will have an indicating flag
                    (\d+)?\s+  # Files will have their size in bytes
                    (.+?)\s*$  # Directory or file name is the remaining text
                    """,
                line,
            ).groups()
            if is_dir:
                for item in self._get_ftp_files(root, "/".join([dir_, name])):
                    yield item
            else:
                yield "/".join(["ftp://" + root, dir_, name])

    @staticmethod
    def _get_bill_id_from_file_path(file_path):
        bill_id = file_path.split("/")[-1].split(".")[0]
        identifier, number = re.search(r"([A-Z]{2}R?)0+(\d+)", bill_id).groups()
        # House and Senate Concurrent and Joint Resolutions files do not contain
        # the 'R' for resolution in file names. This is required to match
        # bill ID's later on.
        if re.match('[HS][CJ]', identifier):
            identifier += 'R'
        return ' '.join([identifier, number])

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("No session specified; using %s", session)

        chambers = [chamber] if chamber else ["upper", "lower"]

        session_code = self._format_session(session)

        self.versions = []
        version_files = self._get_ftp_files(
            self._FTP_ROOT, "bills/{}/billtext/html".format(session_code)
        )
        for item in version_files:
            bill_id = self._get_bill_id_from_file_path(item)
            self.versions.append((bill_id, item))

        self.analyses = []
        analysis_files = self._get_ftp_files(
            self._FTP_ROOT, "bills/{}/analysis/html".format(session_code)
        )
        for item in analysis_files:
            bill_id = self._get_bill_id_from_file_path(item)
            self.analyses.append((bill_id, item))

        self.fiscal_notes = []
        fiscal_note_files = self._get_ftp_files(
            self._FTP_ROOT, "bills/{}/fiscalnotes/html".format(session_code)
        )
        for item in fiscal_note_files:
            bill_id = self._get_bill_id_from_file_path(item)
            self.fiscal_notes.append((bill_id, item))

        self.witnesses = []
        witness_files = self._get_ftp_files(
            self._FTP_ROOT, "bills/{}/witlistbill/html".format(session_code)
        )
        for item in witness_files:
            bill_id = self._get_bill_id_from_file_path(item)
            self.witnesses.append((bill_id, item))

        history_files = self._get_ftp_files(
            self._FTP_ROOT, "bills/{}/billhistory".format(session_code)
        )
        for bill_url in history_files:
            if "house" in bill_url:
                if "lower" in chambers:
                    yield from self.scrape_bill(session, bill_url)
            elif "senate" in bill_url:
                if "upper" in chambers:
                    yield from self.scrape_bill(session, bill_url)

    def scrape_bill(self, session, history_url):
        history_xml = self.get(history_url).text
        root = etree.fromstring(history_xml)

        bill_title = root.findtext("caption")
        if bill_title is None or "Bill does not exist" in history_xml:
            self.warning("Bill does not appear to exist")
            return
        bill_id = " ".join(root.attrib["bill"].split(" ")[1:])

        chamber = self.CHAMBERS[bill_id[0]]

        if bill_id[1] == "B":
            bill_type = ["bill"]
        elif bill_id[1] == "R":
            bill_type = ["resolution"]
        elif bill_id[1:3] == "CR":
            bill_type = ["concurrent resolution"]
        elif bill_id[1:3] == "JR":
            bill_type = ["joint resolution"]
        else:
            raise ScrapeError("Invalid bill_id: %s" % bill_id)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=bill_title,
            classification=bill_type,
        )

        bill.add_source(history_url)

        for subject in root.iterfind("subjects/subject"):
            bill.add_subject(subject.text.strip())

        versions = [x for x in self.versions if x[0] == bill_id]
        for version in versions:
            bill.add_version_link(
                note=self.NAME_SLUGS[version[1][-5]],
                url=version[1],
                media_type="text/html",
            )

        analyses = [x for x in self.analyses if x[0] == bill_id]
        for analysis in analyses:
            bill.add_document_link(
                note="Analysis ({})".format(self.NAME_SLUGS[analysis[1][-5]]),
                url=analysis[1],
                media_type="text/html",
            )

        fiscal_notes = [x for x in self.fiscal_notes if x[0] == bill_id]
        for fiscal_note in fiscal_notes:
            bill.add_document_link(
                note="Fiscal Note ({})".format(self.NAME_SLUGS[fiscal_note[1][-5]]),
                url=fiscal_note[1],
                media_type="text/html",
            )

        witnesses = [x for x in self.witnesses if x[0] == bill_id]
        for witness in witnesses:
            bill.add_document_link(
                note="Witness List ({})".format(self.NAME_SLUGS[witness[1][-5]]),
                url=witness[1],
                media_type="text/html",
            )

        for action in root.findall("actions/action"):
            act_date = datetime.datetime.strptime(
                action.findtext("date"), "%m/%d/%Y"
            ).date()

            action_number = action.find("actionNumber").text
            actor = {"H": "lower", "S": "upper", "E": "executive"}[action_number[0]]

            desc = action.findtext("description").strip()

            if desc == "Scheduled for public hearing on . . .":
                self.warning("Skipping public hearing action with no date")
                continue

            introduced = False

            if desc == "Amended":
                atype = "amendment-passage"
            elif desc == "Amendment(s) offered":
                atype = "amendment-introduction"
            elif desc == "Amendment amended":
                atype = "amendment-amendment"
            elif desc == "Amendment withdrawn":
                atype = "amendment-withdrawal"
            elif desc == "Passed" or desc == "Adopted":
                atype = "passage"
            elif re.match(r"^Received (by|from) the", desc):
                if "Secretary of the Senate" not in desc:
                    atype = "introduction"
                else:
                    atype = "filing"
            elif desc.startswith("Sent to the Governor"):
                # But what if it gets lost in the mail?
                atype = "executive-receipt"
            elif desc.startswith("Signed by the Governor"):
                atype = "executive-signature"
            elif desc.startswith("Effective on"):
                atype = "became-law"
            elif desc == "Vetoed by the Governor":
                atype = "executive-veto"
            elif desc == "Read first time":
                atype = ["introduction", "reading-1"]
                introduced = True
            elif desc == "Read & adopted":
                atype = ["passage"]
                if not introduced:
                    introduced = True
                    atype.append("introduction")
            elif desc == "Passed as amended":
                atype = "passage"
            elif desc.startswith("Referred to") or desc.startswith(
                "Recommended to be sent to "
            ):
                atype = "referral-committee"
            elif desc == "Reported favorably w/o amendment(s)":
                atype = "committee-passage"
            elif desc == "Filed":
                atype = "filing"
            elif desc == "Read 3rd time":
                atype = "reading-3"
            elif desc == "Read 2nd time":
                atype = "reading-2"
            elif desc.startswith("Reported favorably"):
                atype = "committee-passage-favorable"
            else:
                atype = None

            act = bill.add_action(
                action.findtext("description"),
                act_date,
                chamber=actor,
                classification=atype,
            )

            if atype and "referral-committee" in atype:
                repls = ["Referred to", "Recommended to be sent to "]
                ctty = desc
                for r in repls:
                    ctty = ctty.replace(r, "").strip()
                act.add_related_entity(name=ctty, entity_type="organization")

        for author in root.findtext("authors").split(" | "):
            if author != "":
                bill.add_sponsorship(
                    author, classification="primary", entity_type="person", primary=True
                )
        for coauthor in root.findtext("coauthors").split(" | "):
            if coauthor != "":
                bill.add_sponsorship(
                    coauthor,
                    classification="cosponsor",
                    entity_type="person",
                    primary=False,
                )
        for sponsor in root.findtext("sponsors").split(" | "):
            if sponsor != "":
                bill.add_sponsorship(
                    sponsor,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )
        for cosponsor in root.findtext("cosponsors").split(" | "):
            if cosponsor != "":
                bill.add_sponsorship(
                    cosponsor,
                    classification="cosponsor",
                    entity_type="person",
                    primary=False,
                )

        if root.findtext("companions"):
            self._get_companion(bill)

        yield bill

    def _get_companion(self, bill):
        url = self.companion_url.format(
            self._format_session(bill.legislative_session),
            self._format_bill_id(bill.identifier),
        )
        page = self.lxmlize(url)
        links = page.xpath('//table[@id="Table6"]//a')
        for link in links:
            parsed = urlparse.urlparse(link.attrib["href"])
            query = urlparse.parse_qs(parsed.query)
            bill.add_related_bill(
                identifier=query["Bill"][0],
                legislative_session=query["LegSess"][0],
                relation_type="companion",
            )

    def _format_session(self, session):
        if len(session) == 2:
            session = session + "R"
        assert len(session) == 3, "Unable to handle the session name"
        return session

    def _format_bill_id(self, bill_id):
        return bill_id.replace(" ", "")
