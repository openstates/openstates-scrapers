import re
import datetime
import string
import urllib3
from ftplib import FTP

from io import BytesIO

import fitz

from openstates.scrape import Scraper, VoteEvent as Vote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CTVoteScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        yield from self.scrape_votes(session, chambers)

    def scrape_votes(self, session, chambers):
        chamber_map = {"lower": "h", "upper": "s"}

        pdf_urls = []

        ftp_host = "ftp.cga.ct.gov"
        ftp = FTP(ftp_host)
        ftp.login()

        for chamber in chambers:
            ftp_uri = f"/{session}/vote/{chamber_map[chamber]}/pdf/"
            ftp.cwd(ftp_uri)
            files = ftp.nlst()
            pdf_urls += [
                (f"https://www.cga.ct.gov{ftp_uri}{file_name}", session, chamber)
                for file_name in files
            ]

        ftp.close()

        for pdf_url, session, chamber in pdf_urls:
            yield from self.parse_vote(pdf_url, session, chamber)

    def parse_vote(self, url, session, vote_chamber):
        try:
            response = self.get(url, verify=False)
        except Exception as e:
            self.error(f"Failed request in {url} - {e}")
            return

        pdf_content = BytesIO(response.content)
        doc = fitz.open("pdf", pdf_content)

        pdf_text = doc[0].get_text()

        bill_re = re.compile(r"R\d+(?P<prefix>[A-Z]+)0+(?P<number>\d+)")
        bill_number_match = bill_re.search(url)
        if not bill_number_match:
            # At least once a vote PDF seems to be generated in error
            # see ex: https://www.cga.ct.gov/2025/vote/s/pdf/2025SV-00035-R00-SV.PDF
            self.error(f"Failed to find bill number in url {url}, cannot parse vote")
            return
        bill_data = bill_number_match.groupdict()
        bill_id = bill_data["prefix"] + bill_data["number"]

        voters_re = re.compile(r"(?P<type>Y|N|X|A)(\s+\d+)?\s+(?P<name>[^\n]+)")
        voters = [t.groupdict() for t in voters_re.finditer(pdf_text)]

        yes_re = re.compile(r"Those voting Yea[\s\.]+(?P<count>\d+)")
        yes_count = int(yes_re.search(pdf_text).groupdict()["count"])

        no_re = re.compile(r"Those voting Nay[\s\.]+(?P<count>\d+)")
        no_count = int(no_re.search(pdf_text).groupdict()["count"])

        other_re = re.compile(r"Those absent and not voting[\s\.]+(?P<count>\d+)")
        other_count = int(other_re.search(pdf_text).groupdict()["count"])

        need_re = re.compile(
            r"Necessary for (?P<classification>.*?)[\s\.]+(?P<count>\d+)"
        )
        needs = need_re.search(pdf_text).groupdict()
        need_count = int(needs["count"])

        date_re = re.compile(r".*Taken\s+on\s+(\d+/\s?\d+)")
        date = date_re.search(pdf_text).group(1)
        date = date.replace(" ", "")
        date = datetime.datetime.strptime(date + " " + session, "%m/%d %Y").date()
        motion_text = "Senate Roll Call Vote" if "SV" in url else "House Roll Call Vote"

        vote = Vote(
            chamber=vote_chamber,
            start_date=date,
            motion_text=motion_text,
            result="pass" if yes_count > need_count else "fail",
            classification="passage",
            bill=bill_id,
            bill_chamber="upper" if bill_id[0] == "S" else "lower",
            legislative_session=session,
        )
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("absent", other_count)
        vote.add_source(url)
        vote.dedupe_key = url

        for voter in voters:
            name = string.capwords(voter["name"])
            v_type = voter["type"]
            if v_type == "Y":
                vote.yes(name)
            elif v_type == "N":
                vote.no(name)
            else:
                vote.vote("absent", name)

        yield vote
