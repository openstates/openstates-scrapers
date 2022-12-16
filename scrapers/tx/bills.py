import datetime
import ftplib
import re
import time
from urllib import parse as urlparse
import xml.etree.cElementTree as etree

from openstates.scrape import Scraper, Bill
from openstates.scrape.base import ScrapeError
from utils import LXMLMixin
from .actions import Categorizer


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

    categorizer = Categorizer()

    def _get_ftp_files(self, dir_):
        """Recursively traverse an FTP directory, returning all files"""
        for i in range(3):
            try:
                ftp = ftplib.FTP(self._FTP_ROOT)
                break
            except (EOFError, ftplib.error_temp):
                time.sleep(2**i)
        else:
            raise Exception

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
                for item in self._get_ftp_files("/".join([dir_, name])):
                    yield item
            else:
                yield "/".join(["ftp://" + self._FTP_ROOT, dir_, name])

    @staticmethod
    def _get_bill_id_from_file_path(file_path):
        bill_id = file_path.split("/")[-1].split(".")[0]
        identifier, number = re.search(r"([A-Z]{2}R?)0+(\d+)", bill_id).groups()
        # House and Senate Concurrent and Joint Resolutions files do not contain
        # the 'R' for resolution in file names. This is required to match
        # bill ID's later on.
        if re.match("[HS][CJ]", identifier):
            identifier += "R"
        return " ".join([identifier, number])

    def scrape(self, session=None, chamber=None):
        chambers = [chamber] if chamber else ["upper", "lower"]

        session_code = self._format_session(session)

        self.witnesses = []
        witness_files = self._get_ftp_files(
            "bills/{}/witlistbill/html".format(session_code)
        )
        for item in witness_files:
            bill_id = self._get_bill_id_from_file_path(item)
            self.witnesses.append((bill_id, item))

        history_files = self._get_ftp_files("bills/{}/billhistory".format(session_code))
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

        bill_id_for_url = bill_id.replace(" ", "")
        bill.add_source(
            f"https://capitol.texas.gov/BillLookup/History.aspx?LegSess={session}&Bill={bill_id_for_url}"
        )

        for subject in root.iterfind("subjects/subject"):
            bill.add_subject(subject.text.strip())

        for version in root.iterfind("billtext/docTypes/bill/versions/version"):
            if not version:
                continue

            note = version.find("versionDescription").text
            html_url = version.find("WebHTMLURL").text
            bill.add_version_link(note=note, url=html_url, media_type="text/html")
            pdf_url = version.find("WebPDFURL").text
            bill.add_version_link(note=note, url=pdf_url, media_type="application/pdf")

        for analysis in root.iterfind("billtext/docTypes/analysis/versions/version"):
            if not analysis:
                continue

            description = analysis.find("versionDescription").text
            html_url = analysis.find("WebHTMLURL").text
            bill.add_document_link(
                note="Analysis ({})".format(description),
                url=html_url,
                media_type="text/html",
            )

        for fiscal_note in root.iterfind(
            "billtext/docTypes/fiscalNote/versions/version"
        ):
            if not fiscal_note:
                continue

            description = fiscal_note.find("versionDescription").text
            html_url = fiscal_note.find("WebHTMLURL").text
            bill.add_document_link(
                note="Fiscal Note ({})".format(description),
                url=html_url,
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

            action_attr = self.categorizer.categorize(desc)
            atype = action_attr["classification"]

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
            if re.search(r"\S+", author.strip()) is not None:
                bill.add_sponsorship(
                    author, classification="primary", entity_type="person", primary=True
                )
        for coauthor in root.findtext("coauthors").split(" | "):
            if re.search(r"\S+", coauthor.strip()) is not None:
                bill.add_sponsorship(
                    coauthor,
                    classification="cosponsor",
                    entity_type="person",
                    primary=False,
                )
        for sponsor in root.findtext("sponsors").split(" | "):
            if re.search(r"\S+", sponsor.strip()) is not None:
                bill.add_sponsorship(
                    sponsor,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )
        for cosponsor in root.findtext("cosponsors").split(" | "):
            if re.search(r"\S+", cosponsor.strip()) is not None:
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
                legislative_session=query["LegSess"][0].replace("R", ""),
                relation_type="companion",
            )

    def _format_session(self, session):
        if len(session) == 2:
            session = session + "R"
        assert len(session) == 3, "Unable to handle the session name"
        return session

    def _format_bill_id(self, bill_id):
        return bill_id.replace(" ", "")
