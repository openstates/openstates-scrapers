import re
from datetime import datetime
from io import BytesIO

import fitz
import scrapelib
from lxml import html

from openstates.scrape import Scraper, VoteEvent

# Senate vote header
s_vote_header = re.compile(r"(YES)|(NO)|(ABS)|(EXC)|(REC)")
# House vote header
h_vote_header = re.compile(r"(YEA(?!S))|(NAY(?!S))|(EXCUSED(?!:))|(ABSENT(?!:))")

# Date regex for senate and house parser
date_regex = re.compile(r"([0-1][0-9]/[0-3][0-9]/\d+)")


class NMVoteScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber else ["upper", "lower"]

        for chamber in chambers:
            yield from self.scrape_vote(chamber, session)

    def scrape_vote(self, chamber, session):
        """most document types (+ Votes) are in this common directory go
        through it and attach them to their related bills"""
        session_path = self.session_slug(session)

        doc_path = "https://www.nmlegis.gov/Sessions/{}/votes/".format(session_path)

        self.info("Getting doc at {}".format(doc_path))
        content = self.get(doc_path).text
        tree = html.fromstring(content)

        # all links but first one
        for fname in tree.xpath("//a/text()")[1:]:
            # If filename includes COPY or # or not PDF, skips them
            if "COPY" in fname or "#" in fname or "PDF" not in fname:
                continue

            # Delete any errant words found following the file name
            fname = fname.split(" ")[0]

            match = re.match(r"([A-Z]+)0*(\d{1,4})([^.]*)", fname.upper())
            if match is None:
                self.warning("No match, skipping")
                continue

            bill_type, bill_num, suffix = match.groups()

            # adapt to bill_id format
            bill_id = bill_type + " " + bill_num

            # votes
            if ("SVOTE" in suffix and chamber == "upper") or (
                "HVOTE" in suffix and chamber == "lower"
            ):
                sv_doc = self.scrape_document(doc_path + fname)
                if not sv_doc:
                    continue

                vote = self.parse_vote(
                    sv_doc, doc_path + fname, session, bill_id, chamber
                )
                if not vote:
                    self.warning(
                        "Bad parse on the {} vote for {}".format(chamber, bill_id)
                    )
                else:
                    yield vote

    def scrape_document(self, filelocation):
        """Downloads PDF file content and converts into PyMuPDF object."""
        try:
            response = self.get(url=filelocation)
            doc = fitz.open("pdf", BytesIO(response.content))
        except scrapelib.HTTPError:
            self.warning("Request failed: {}".format(filelocation))
            return

        return doc

    def parse_vote(self, doc, url, session, bill_id, chamber):
        headers = ["yes", "no", "absent", "excused", "other"]
        # Add new columns as they appear to be safe
        # doc[0] -> page 1
        # get_text() function returns all text from page
        pdf_text_content = doc[0].get_text()
        # finds tables from page and returns TableFinder object.
        # TableFinder object has tables property.
        pdf_tables = doc[0].find_tables()
        # convert table to pandas's DataFrame
        if len(pdf_tables.tables) == 0:
            self.warning(f"Not found tables from {url}")
            return

        pdf_table_df = pdf_tables.tables[0].to_pandas()

        total_votes, vote_record = self.extract_votes(
            headers, pdf_text_content, pdf_table_df
        )

        motion_text = "senate passage" if chamber == "upper" else "house passage"

        vote = self.build_vote(session, bill_id, url, vote_record, chamber, motion_text)
        self.validate_vote(headers, total_votes, vote_record)
        return vote

    def extract_votes(self, headers, pdf_text_content, pdf_table_df):
        # Extract the vote data using pymupdf library
        # pdf_text_content: text content of pdf
        # pdf_table_df: table content of pdf
        vote_record = dict()

        # extract date string from pdf text content
        # 2 cases: mm/dd/yy and mm/dd/yyyy
        # if new case would be found, raises ValueError exception
        date_string = date_regex.search(pdf_text_content).group()
        if len(date_string) == 8:
            vote_record["date"] = datetime.strptime(date_string, "%m/%d/%y")
        elif len(date_string) == 10:
            vote_record["date"] = datetime.strptime(date_string, "%m/%d/%Y")
        else:
            raise ValueError(f"Wrong date string in {date_string}")

        # divide dataframe into 2 parts: left and right
        columns = pdf_table_df.columns.tolist()
        columns_len = int(len(columns) / 2)
        df_left = pdf_table_df[columns[0:columns_len]]
        df_right = pdf_table_df[columns[columns_len:]]
        columns = self.get_correct_columns(columns[0:columns_len])
        df_left.columns = df_right.columns = columns

        # HVOTE Case
        if h_vote_header.search(pdf_text_content):
            total_votes = {}
            total_votes["yes"] = re.search(r"YE.*?:\s?(\d+)", pdf_text_content).group(1)
            total_votes["no"] = re.search(r"NA.*?:\s?(\d+)", pdf_text_content).group(1)
            total_votes["absent"] = int(
                re.search(r"AB.*?:\s?(\d+)", pdf_text_content).group(1)
            )
            total_votes["excused"] = int(
                re.search(r"EX.*?:\s?(\d+)", pdf_text_content).group(1)
            )
            total_votes["other"] = int(
                re.search(r"PNV:\s?(\d+)", pdf_text_content).group(1)
            )
        # SVOTE Case
        elif s_vote_header.search(pdf_text_content):
            total_votes = df_right[df_right["name"].isin(["TOTAL =>"])]
            total_votes = total_votes[headers].to_dict("records")[0]

        # Get the voters by vote type
        for header in headers:
            vote_record[header] = (
                df_left[df_left[header].isin(["X"])]["name"].tolist()
                + df_right[df_right[header].isin(["X"])]["name"].tolist()
            )

        return total_votes, vote_record

    def get_correct_columns(self, header):
        # replace pandas columns to the predefnied columns
        # the order can be different
        # NEW HEADER: [name yes no absent excused other]
        # HVOTE : [0-REPRESENTATIVE 1-YEA 2-NAY 3-PNV 4-EXC 5-ABSENT]
        # SVOTE : [Col0 1-YES 2-NO 3-EXC 4-ABS 5-REC]
        new_header = []
        header_map = {
            "Y": "yes",
            "N": "no",
            "A": "absent",
            "E": "excused",
        }
        for h in header:
            if h.startswith("Col") or "REPR" in h:
                new_header.append("name")
            elif "-" in h and (first_letter := h.split("-")[1][0]):
                new_header.append(header_map.get(first_letter, "other"))

        return new_header

    def session_slug(self, session):
        session_type = "Special" if session.endswith("S") else "Regular"
        return "{}%20{}".format(session[2:4], session_type)

    def build_vote(self, session, bill_id, url, vote_record, chamber, motion_text):
        # When they vote in a substitute they mark it as XHB
        bill_id = bill_id.replace("XHB", "HB")
        passed = len(vote_record["yes"]) > len(vote_record["no"])
        vote_event = VoteEvent(
            result="pass" if passed else "fail",
            chamber=chamber,
            start_date=vote_record["date"].strftime("%Y-%m-%d"),
            motion_text=motion_text,
            classification="passage",
            legislative_session=session,
            bill=bill_id,
            bill_chamber="upper" if bill_id[0] == "S" else "lower",
        )
        vote_event.dedupe_key = url
        vote_event.set_count("yes", len(vote_record["yes"]))
        vote_event.set_count("no", len(vote_record["no"]))
        vote_event.set_count("excused", len(vote_record["excused"]))
        vote_event.set_count("absent", len(vote_record["absent"]))
        vote_event.set_count("other", len(vote_record["other"]))
        for vote_type in ["yes", "no", "excused", "absent", "other"]:
            for voter in vote_record[vote_type]:
                vote_event.vote(vote_type, voter)

        vote_event.add_source(url)
        return vote_event

    def validate_vote(self, headers, sane, vote_record):
        # Make sure the parsed vote totals match up with counts in the
        # total field
        result = all(
            [int(sane[header]) == len(vote_record[header]) for header in headers]
        )
        if not result:
            raise ValueError("Votes were not parsed correctly")
