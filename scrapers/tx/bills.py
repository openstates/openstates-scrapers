import datetime
import ftplib
import re
import time
import urllib3
import itertools

from io import BytesIO
from urllib import parse as urlparse

import xml.etree.cElementTree as etree
import fitz

from openstates.scrape import Scraper, Bill
from openstates.scrape.base import ScrapeError
from utils import LXMLMixin
from .actions import Categorizer


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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

        # self.witnesses = []
        # witness_files = self._get_ftp_files(
        #     "bills/{}/witlistbill/html".format(session_code)
        # )
        # for item in witness_files:
        #     bill_id = self._get_bill_id_from_file_path(item)
        #     self.witnesses.append((bill_id, item))

        history_files = self._get_ftp_files("bills/{}/billhistory".format(session_code))
        for bill_url in history_files:
            if "house" in bill_url:
                if "lower" in chambers:
                    yield from self.scrape_bill(session, bill_url)
                    break
            elif "senate" in bill_url:
                if "upper" in chambers:
                    yield from self.scrape_bill(session, bill_url)
                    break

    def scrape_bill(self, session, history_url):
        print(history_url)
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
        bill_history_url = f"https://capitol.texas.gov/BillLookup/History.aspx?LegSess={session}&Bill={bill_id_for_url}"
        bill.add_source(bill_history_url)

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

        # witnesses = [x for x in self.witnesses if x[0] == bill_id]
        # for witness in witnesses:
        #     bill.add_document_link(
        #         note="Witness List ({})".format(self.NAME_SLUGS[witness[1][-5]]),
        #         url=witness[1],
        #         media_type="text/html",
        #     )

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

        # Parse Votes
        # yield from self.scrape_vote(bill_id, bill_history_url)
        yield from self.scrape_vote(
            "SB 2429",
            "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=88R&Bill=SB2429",
        )

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

    def scrape_vote(self, bill_id, bill_history_url):
        page = self.lxmlize(bill_history_url)
        for vote_href in page.xpath('//tr[contains(@id, "vote")]/td/a'):
            vote_name = vote_href.text_content()
            if vote_name != "Record vote":
                continue
            vote_url = (
                vote_href.attrib["href"].replace("pdf", "html").replace("PDF", "HTM")
            )
            yield from self.parse_vote(vote_url, bill_id)

    def parse_vote(self, url, bill_id):
        if "page=" not in url:
            self.error("No page number for {}".format(url))

        page_number = url.split("page=")[-1]
        try:
            response = self.get(url, verify=False)
        except Exception as e:
            self.error(f"Failed request in {url} - {e}")
            return
        pdf_content = BytesIO(response.content)
        doc = fitz.open("pdf", pdf_content)
        page = doc[int(page_number) - 1]
        pdf_text = page.get_text()

        next_page = doc[int(page_number)]
        next_pdf_text = next_page.get_text()

        pdf_text = self.clear_pdf_text(pdf_text.strip())
        next_pdf_text = self.clear_pdf_text(next_pdf_text.strip())

        bill_pattern = r"\b(CSSB|CSHB|HB|SB|SCR|SJR|SR|HCR|HJR|HR|HOUSE.BILL|SENATE.BILL)[^\d]+(\d+)\b"
        voting_pattern1 = (
            r"(\d+)\s+Yeas,\s+(\d+)\s+Nays(?:,\s+(\d+)\s+Present,\s+not voting)?"
        )
        voting_pattern2 = (
            r"Yeas.(\d+),\s+Nays.(\d+)(?:,\s+Present,\s+not voting.(\d+))?"
        )

        skip_line_cnt = 0
        alt_bill_id = bill_id
        results = []
        may_results = []
        for line_num, line_text in enumerate(pdf_text):
            if skip_line_cnt > 0:
                skip_line_cnt = skip_line_cnt - 1
                continue

            skip_line_cnt = 0
            bill_match = re.search(bill_pattern, line_text)
            if bill_match:
                alt_bill_id = (
                    bill_match.group(0)
                    .replace("CS", "")
                    .replace("HOUSE BILL", "HB")
                    .replace("SENATE BILL", "SB")
                    .strip()
                )

            voting_match = re.search(voting_pattern1, line_text) or re.search(
                voting_pattern2, line_text
            )
            if voting_match:
                next_line_num = 0
                yeas, nays, present_not_voting = voting_match.groups()
                present_not_voting = present_not_voting or "0"

                yeas = int(yeas)
                nays = int(nays)
                present_not_voting = int(present_not_voting)

                next_text = (
                    pdf_text[line_num + 1] if line_num + 1 < len(pdf_text) else ""
                )
                yea_voters, go_next_yea = self.extract_voter_list(
                    "Yeas", next_text, yeas
                )
                if go_next_yea:
                    yea_voters, _ = self.extract_voter_list(
                        "Yeas", next_text + next_pdf_text[next_line_num], yeas
                    )
                    next_line_num += 1
                if len(yea_voters) != 0:
                    skip_line_cnt = 1
                next_text = (
                    pdf_text[line_num + skip_line_cnt + 1]
                    if line_num + skip_line_cnt + 1 < len(pdf_text)
                    else ""
                )
                nay_voters, go_next_nay = self.extract_voter_list(
                    "Nays",
                    (next_pdf_text[next_line_num] if next_line_num else next_text),
                    nays,
                )
                if next_line_num > 0:
                    next_line_num += 1
                if go_next_nay:
                    nay_voters, go_next_nay = self.extract_voter_list(
                        "Nays", next_text + next_pdf_text[0], nays
                    )
                    next_line_num = 1
                if len(nay_voters) != 0:
                    skip_line_cnt += 1
                next_text = (
                    pdf_text[line_num + skip_line_cnt + 1]
                    if line_num + skip_line_cnt + 1 < len(pdf_text)
                    else ""
                )
                present_not_voting_voters, go_next_nv = self.extract_voter_list(
                    "Present, not voting",
                    (next_pdf_text[next_line_num] if next_line_num else next_text),
                    present_not_voting,
                )
                if next_line_num > 0:
                    next_line_num += 1
                if go_next_nv:
                    present_not_voting_voters, go_next_nv = self.extract_voter_list(
                        "Present, not voting",
                        next_text + next_pdf_text[0],
                        present_not_voting,
                    )
                    next_line_num = 1
                # if len(present_not_voting_voters) != 0:
                #     skip_line_cnt += 1
                # next_text = (
                #     pdf_text[line_num + skip_line_cnt + 1]
                #     if line_num + skip_line_cnt + 1 < len(pdf_text)
                #     else ""
                # )
                # if next_line_num > 0:
                #     next_line_num += 1
                # absent_excused_voters, go_next_exc = self.extract_voter_list(
                #     "Absent, Excused",
                #     (next_pdf_text[next_line_num] if next_line_num else next_text),
                #     -1,
                # )
                # if go_next_exc:
                #     absent_excused_voters, go_next_exc = self.extract_voter_list(
                #         "Absent, Excused", next_text + next_pdf_text[0], -1
                #     )
                #     next_line_num = 1
                # if len(absent_excused_voters) != 0:
                #     skip_line_cnt += 1
                # next_text = (
                #     pdf_text[line_num + skip_line_cnt + 1]
                #     if line_num + skip_line_cnt + 1 < len(pdf_text)
                #     else ""
                # )
                # if next_line_num > 0:
                #     next_line_num += 1
                # absent_voters, go_next_abs = self.extract_voter_list(
                #     "Absent",
                #     (next_pdf_text[next_line_num] if next_line_num else next_text),
                #     -1,
                # )
                # if go_next_abs:
                #     absent_voters, go_next_abs = self.extract_voter_list(
                #         "Absent, Excused", next_text + next_pdf_text[0], -1
                #     )
                #     next_line_num = 1
                # if len(absent_voters) != 0:
                #     skip_line_cnt += 1

                if alt_bill_id == bill_id:
                    results.append(
                        {
                            "yes": yeas,
                            "no": nays,
                            "other": present_not_voting,
                            # + len(absent_voters)
                            # + len(absent_excused_voters),
                            "voters": {
                                "yes": yea_voters,
                                "no": nay_voters,
                                "not voting": present_not_voting_voters,
                                # "absent": absent_voters,
                                # "excused": absent_excused_voters,
                            },
                        }
                    )
                else:
                    may_results.append(
                        {
                            "yes": yeas,
                            "no": nays,
                            "other": present_not_voting,
                            # + len(absent_voters)
                            # + len(absent_excused_voters),
                            "voters": {
                                "yes": yea_voters,
                                "no": nay_voters,
                                "not voting": present_not_voting_voters,
                                # "absent": absent_voters,
                                # "excused": absent_excused_voters,
                            },
                        }
                    )

        print(pdf_text)
        print(results)
        print(may_results)
        yield {}

    # Extract voter names
    def clear_pdf_text(self, text):
        def replace_str(match):
            return match.group(0).replace("i", " ")

        bill_pattern = r"\b(CSSB|CSHB|HB|SB|SCR|SJR|SR|HCR|HJR|HR|HOUSE.BILL|SENATE.BILL)[^\d]+(\d+)\b"
        pdf_text = re.sub(
            bill_pattern,
            replace_str,
            text,
        )
        pdf_text = re.sub(
            r"i\d+",
            replace_str,
            pdf_text.replace("ii", " "),
        )
        ignore_patterns = [
            r"^\d+$",
            r"\b\d{1,3}(?:st|nd|rd|th) LEGISLATURE — [A-Z]+ SESSION\b",
            r"\b\d{1,3}(?:st|nd|rd|th) Day\b",
            r"\b[A-Za-z]+, [A-Za-z]+ \d{1,2}, \d{4}\b",
            r"\b(?:HOUSE|SENATE) JOURNAL\b",
            r"\b\d{1,3}(?:st|nd|rd|th) Day\b",
        ]
        ignore_cnt = 0
        for line_text in pdf_text.split("\n"):
            for ignore_pattern in ignore_patterns:
                if re.search(ignore_pattern, line_text, re.IGNORECASE):
                    ignore_cnt -= 1
                    break

        pdf_text = [
            line.replace("\n", " ")
            for line in re.split("\.\n", "\n".join(pdf_text.split("\n")[0:ignore_cnt]))
        ]

        return pdf_text

    def extract_voter_list(self, prefix, text, estimate_cnt):
        go_next = False
        result = []
        match = re.search(rf"{prefix} — ([\s\S]+)$", text)
        if match:
            result = [name.strip() for name in match.group(1).split(";")]
        match = re.search(rf"{prefix}: ([\s\S]+)$", text)
        if match:
            result = [name.strip() for name in match.group(1).split(",")]

        if len(result) != estimate_cnt and estimate_cnt != -1:
            go_next = True
        if len(text.strip()) == 0:
            go_next = True
        if estimate_cnt == 0:
            go_next = False
            result = []
        return result, go_next
