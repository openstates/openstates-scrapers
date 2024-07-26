from spatula import (
    URL,
    HtmlListPage,
    PdfPage,
    HtmlPage,
    XPath,
)
from openstates.scrape import VoteEvent, Scraper
import re
import pytz
import datetime as dt


class VoteTotalMismatch(Exception):
    def __init__(self):
        super().__init__("Vote total mismatch")


class MAVoteScraper(Scraper):
    def scrape(self, session=None):
        # yield from HouseJournalDirectory().do_scrape()
        yield from SenateJournalDirectory().do_scrape()


class HouseJournalDirectory(HtmlPage):
    source = URL("http://malegislature.gov/Journal/House/192", verify=False)

    def process_page(self):
        # find all links to a file called RollCalls
        # One of these files exists for each year directory
        roll_calls = [
            x for x in XPath("//a/@href").match(self.root) if x.endswith("RollCalls")
        ]
        for rc in roll_calls:
            vote_events = HouseRollCall(source=URL(rc, verify=False)).do_scrape()
            for vote_event in vote_events:
                vote_event.add_source(self.source.url, note="House journal listing")
                yield vote_event


class SenateJournalDirectory(HtmlListPage):
    source = URL("https://malegislature.gov/Journal/Senate", verify=False)
    votes_list = []

    def process_page(self):
        # Find all link to each month
        month_links = XPath("//a[@aria-controls='journalList']/@href").match(self.root)
        for month_link in month_links:
            vote_events = SenateJournalMonth(
                source=URL(month_link, verify=False),
                votes_list=self.votes_list
            ).do_scrape()
            for vote_event in vote_events:
                # vote_event.add_source(self.source.url, note="Senate jouenal listing")
                yield vote_event


class SenateJournalMonth(HtmlListPage):

    def __init__(self, source, votes_list):
        super().__init__(source=source)
        self.votes_list = votes_list

    def process_page(self):
        journal_pdf_links = XPath("//tr/td/a/@href").match(self.root)
        for journal_pdf_link in journal_pdf_links:
            # if journal_pdf_link in (
            #     "https://malegislature.gov/Journal/Senate/193/806/sj03302023_1100AM.pdf",
            #     "https://malegislature.gov/Journal/Senate/193/768/sj03232023_0100PM.pdf",
            # ):
            yield SenateJournal(source=URL(journal_pdf_link, verify=False),
                                votes_list=self.votes_list
                                )


class SenateJournal(PdfPage):
    motion_and_vote_total = r"((?P<rawmotion>.{900}))\(yeas\s*(?P<firstyeatotal>\d+)\s*(?:-|to)\s*nays.(?P<firstnaytotal>\d+)\)"
    vote_id = r"\[Yeas\.?.and.Nays\.?.No\.?.(?P<votenumber>\d+)\]"
    vote_section = r"YEAS(?P<yealines>.*?)(?P<secondyeatotal>\d+)\.(?P<extrayealines>.*?)NAYS(?P<naylines>.*?)(?P<secondnaytotal>\d+)(?:(?P<extranaylines>.{0,30}?)ABSENT OR NOT VOTING(?P<nvlines>.*?)(?P<secondnvtotal>\d+))?"

    motion_and_vote_total_re = re.compile(motion_and_vote_total, re.DOTALL)
    vote_id_re = re.compile(vote_id, re.DOTALL)
    vote_section_re = re.compile(vote_section, re.DOTALL)

    total_vote_re = re.compile(f"{motion_and_vote_total}.*?{vote_id}.*?{vote_section}", re.DOTALL)

    not_name_re = re.compile(r"^(\d|UNCORRECTED|Joint Rules|\.|Real ID,-- homeless"
                             r"|Pharmacists,-- PrEP\."
                             r"|Brewster,-- land\."
                             r"|Provincetown,-wastewater"
                             r")"
                             )
    text = None

    precise_motion = r"question on\s+(.+)\s+was determined"
    precise_motion_re = re.compile(precise_motion, re.DOTALL)

    bill_id = r"(House|Senate),\s+No\.\s+(\d+)"
    bill_id_re = re.compile(bill_id, re.DOTALL)

    motion_classification = {
        r"passing.+engross": "engrossment",
        r"adoption.+amendment": "amendment-passage",
        r"acceptance.+report": "report-acceptance",
        r"passing.+enacted": "passage",
        r"approving.+plan": "passage",
    }

    date_time_re = re.compile(r"sj(\d{8})_(?:\d{3,4}[AM|PM])\.pdf")

    journal_date = None

    def __init__(self, source, votes_list):
        super().__init__(source=source)
        self.votes_list = votes_list

    def process_date(self):
        # Find the match
        datetime_match = self.date_time_re.search(self.source.url)

        if datetime_match:
            date_str = datetime_match.group(1)
            vote_date = dt.datetime.strptime(date_str, "%Y%m%d")
            formatted_date = vote_date.strftime("%Y-%m-%d")

            print("Formatted date:", formatted_date)
            return formatted_date

        else:
            raise Exception(f"Datetime with known format not in pdf url: "
                            f"{self.source.url}")

    def process_page(self):
        vote_date = self.process_date()

        # Remove special characters that look like the - character
        self.text = self.text.replace("–", "-").replace("−", "-").replace("—", "-")

        # Search for each of the three components of the larger regex separately.
        votes_mt = self.motion_and_vote_total_re.findall(self.text)
        votes_s = self.vote_section_re.findall(self.text)
        votes_id = self.vote_id_re.findall(self.text)
        # Check to make sure they all found the same number of matches
        # If they disagree on number of matches, the scraper will not get
        # the data correctly so emit a warning and skip this pdf.
        if not (len(votes_mt) == len(votes_s) == len(votes_id)):
            self.logger.warn(f"\nCould not accurately parse votes for "
                             f"{self.source.url}\n"
                             f"len(votes_mt):{len(votes_mt)}\n"
                             f"len(votes_s):{len(votes_s)}\n"
                             f"len(votes_id):{len(votes_id)}\n"
                             f"{self.text}")
        else:
            # Run full regex search.
            votes = self.total_vote_re.finditer(self.text)
            votes = [self.parse_match(v) for v in votes]
            # yield from
            print("\n\n".join([str(x) for x in votes]))
            # print(self.source.url)

    def parse_match(self, match):

        # TODO: to get bill_id, it needs to treat each vote separately
        #  and be able to search backwards in the text for most proximal
        #  bill_id format match (regex or another approach may be needed)

        # You can ignore the current code that attempts to get a bill_id match, as its
        # about to be deprecated by the below described solution.

        """
        The reason why it can't just grab it in the current solution is you would have to go
        far back enough into the prior paragraphs to be able to find the bill_id, but not
        too far back because then it prevents matches on other votes when vote lines are
        positioned too close together in the PDF. This is easier to do for the motion text
        than the bill_id

        That is why the motion_and_vote_total regex pattern defined at the top of this class
        gets 900 characters preceding each instance of "(yeas ## - nays ##)". It needs to go
        far back enough to get the motion text found in between "question on" and "was determined",
        but I have had to find a sweet spot where it gets the motion text without preventing matches
        on proximally preceding votes.

        Here's the solution for getting the bill_ids which I'm currently working on:

        I have a helper function that uses the raw_motion_text essentially as an indexing point to divide
        via a split() of the `self.text` on that substring, and then use a regex that gets the last
        instance of a bill_id format in the `self.text`, i.e. bill_id_match = re.findall(pattern, text)[-1]

        This should get us the accurate data because the last bill_id occurrence in the text before
        the vote lines is the bill that is being voted upon, in every case I have found.
        """
        raw_motion_text = match.group("rawmotion")
        bill_id_match = self.bill_id_re.search(raw_motion_text)
        if not bill_id_match:
            # raise Exception(f"no bill id in {raw_motion_text} at {self.source.url}")
            self.logger.warn(f"Could not find bill_id at {self.source.url}")
        else:
            print("\n\n\n" + bill_id_match.group(2) + "\n\n\n")

        motion_text = self.precise_motion_re.search(raw_motion_text).group(1)
        single_line_motion = motion_text.replace("\n", " ")

        normalized_motion = single_line_motion.capitalize()

        vote_classification = None
        for pattern, classification in self.motion_classification.items():
            if re.compile(pattern).search(single_line_motion):
                vote_classification = classification
                break

        if not vote_classification:
            raise Exception(
                f"""
                No vote_classification from {single_line_motion}" in journal at {self.source.url}
                """
            )

        # Get the total counts
        first_total_yea = int(match.group("firstyeatotal"))
        first_total_nay = int(match.group("firstnaytotal"))
        total_yea = int(match.group("secondyeatotal"))
        total_nay = int(match.group("secondnaytotal"))

        # # Get non-voting total count, but section may be missing
        # possible_total_nv = match.group("secondnvtotal")
        # if possible_total_nv is None:
        #     possible_total_nv = "0"
        # total_nv = int(possible_total_nv)

        vote_number = match.group("votenumber")

        # Get list of voter names for each section
        yea_voters = self.find_names(match.group("yealines"))
        nay_voters = self.find_names(match.group("naylines"))
        yea_voters.extend(self.find_names(match.group("extrayealines")))

        # extre nay lines section may be missing
        possible_extra_nay_voters = match.group("extranaylines")
        if possible_extra_nay_voters is None:
            possible_extra_nay_voters = ""
        nay_voters.extend(self.find_names(possible_extra_nay_voters))

        # non-voting voter name section may be missing
        possible_nv_voters = match.group("nvlines")
        if possible_nv_voters is None:
            possible_nv_voters = ""
        nv_voters = self.find_names(possible_nv_voters)

        data = dict(
            total_yea=total_yea,
            total_nay=total_nay,
            yea_voters=yea_voters,
            nay_voters=nay_voters,
            nv_voters=nv_voters,
            vote_number=vote_number,
            bill_id_match=bill_id_match.group(2) if bill_id_match else None,
            normalized_motion=normalized_motion,
        )
        self.votes_list.append(data)
        print(self.votes_list)

        # TODO: there are a few regex kinks leading to possible miscounts in the vote
        #  tallies (not more than 3 votes off) which could be a problem when trying to
        #  use these counts to determine whether a vote passed/failed.
        #  But given the typical large vote margins between yeas and nays, even the current
        #  occassional miscounts would rarely lead to a false determination of the vote result.
        yea_mismatch = first_total_yea != total_yea
        nay_mismatch = first_total_nay != total_nay
        if yea_mismatch or nay_mismatch:
            print(self.text)
            print(self.source.url)
            print(f"""
            first_total_yea = {first_total_yea}
            total_yea = {total_yea}
            first_total_nay = {first_total_nay}
            total_nay = {total_nay}
            yea_mismatch = {yea_mismatch}
            nay_mismatch = {nay_mismatch}
            {data}
            """)
            raise Exception("ynmismatch")

        # Check that total voters and total votes match up
        yea_matches_miscount = len(yea_voters) - total_yea
        nay_matches_miscount = len(nay_voters) - total_nay
        for miscount in yea_matches_miscount, nay_matches_miscount:
            # Allows for minor miscount in cases of PDF formatting issues
            if abs(miscount) > 1:
                print(self.text)
                print(self.source.url)
                print(f"""
                            yea_voters = {len(yea_voters)}
                            total_yea = {total_yea}
                            nay_voters = {len(nay_voters)}
                            total_nay = {total_nay}
                            yea_matches_miscount = {yea_matches_miscount}
                            nay_matches_miscount = {nay_matches_miscount}
                            {data}
                            """)
                raise Exception("recorded vote totals differ from logs")

        # TODO: comment back in when bill_id and result handling is complete
        # vote = VoteEvent(
        #     chamber="upper",
        #     legislative_session="193",
        #     # start_date=vote_date,
        #     # motion_text=self.motion,
        #     bill=bill_id,
        #     result="pass" if vote_passed else "fail",
        #     classification="passage",
        # )

        return data

    # Finds names in text, ignoring some common phrases and empty lines
    def find_names(self, text):
        text = [x.strip() for x in text.split("\n")]
        text = [x for x in text if x != ""]
        names = [x for x in text if not self.not_name_re.match(x) and "," in x]

        return names


class HouseVoteRecordParser:
    tz = pytz.timezone("US/Eastern")
    total_yea_re = re.compile(r"(\d+) yeas", re.IGNORECASE)
    total_nay_re = re.compile(r"(\d+) nays", re.IGNORECASE)
    total_nv_re = re.compile(r"(\d+) n/v", re.IGNORECASE)
    bill_re = re.compile(r"(h|s)\.? ?(\d+) ?(.*)", re.IGNORECASE)
    number_re = re.compile(r"no\.? ?(\d+)", re.IGNORECASE)

    def __init__(self, vote_text):
        self.votes = []
        self.names = []
        self.time = None
        self.total_yea = None
        self.total_nay = None
        self.total_nv = None
        self.bill_id = None
        self.vote_number = None
        self.motion = None
        self.motion_parts = []
        lines = vote_text.split("\n")
        self.raw = vote_text
        for line in lines:
            self.read_line(line)

    def read_line(self, line):
        line = line.strip()

        # These lines contain no useful info and are skipped
        blank = line in ["\x0c", ""]
        contains_equal = "=" in line
        yea_and_nay = line == "Yea and Nay"
        if blank or contains_equal or yea_and_nay:
            pass

        # Check for vote number. When the vote number is found, we can be sure
        # that all the motion text has been read.
        elif (match := self.number_re.match(line)) is not None:
            self.vote_number = int(match.group(1))
            self.motion = " ".join(self.motion_parts)

        # Check for time
        elif ":" in line:
            when = datetime.datetime.strptime(line, "%m/%d/%Y %I:%M %p")
            when = self.tz.localize(when)
            self.time = when

        # Check for vote totals
        elif (match := self.total_yea_re.match(line)) is not None:
            self.total_yea = int(match.group(1))

        elif (match := self.total_nay_re.match(line)) is not None:
            self.total_nay = int(match.group(1))

        elif (match := self.total_nv_re.match(line)) is not None:
            self.total_nv = int(match.group(1))

        # line is vote type
        # Y is sometimes read as P by the pdf reader.
        elif line in ["Y", "N", "X", "P"]:
            self.votes.append(line)

        # Read the line as motion, motion text may come through as multiple
        # lines so append the line to an array.
        elif self.vote_number is None:
            self.motion_parts.append(line)

        # At this point, the line is assumed to contain a name.

        # Special case where pdf reader mistakenly joins two names together into
        # a single line. This can happen if the first name starts with a double
        # '--'. This can cause the next name in the list to be joined with
        # this line. e.g. "--Jones-Smith" instead of "--Jones--" and "Smith" on
        # separate lines.
        elif line.startswith("--"):
            all_names = [x for x in line[2:].split("-") if x]
            self.names.extend(all_names)

        # The line is a single name, but may be surrounded by '--'
        else:
            self.names.append(line.replace("--", ""))

    # Raises an error or writes warning to logger. Returns true if data is valid
    def error_if_invalid(self):
        votes_match_names = len(self.names) == len(self.votes)
        if not votes_match_names:
            raise VoteTotalMismatch()

    def get_warning(self):
        # Some votes may not have any motion listed
        if not self.motion:
            return (
                f"Found vote with no motion listed, skipping vote #{self.vote_number}"
            )

    def createVoteEvent(self):
        vote_passed = self.total_yea > self.total_nay

        # Check for bill id in motion text
        bill_id = None
        if (match := self.bill_re.match(self.motion)) is not None:
            bill_id = f"{match.group(1)}{match.group(2)}"

        vote = VoteEvent(
            chamber="lower",
            legislative_session="193",
            start_date=self.time,
            motion_text=self.motion,
            bill=bill_id,
            result="pass" if vote_passed else "fail",
            classification="passage",
        )

        vote.set_count("yes", self.total_yea)
        vote.set_count("no", self.total_nay)

        vote_dictionary = {
            "Y": "yes",
            "P": "yes",  # Y's can be misread as P's
            "N": "no",
            "X": "not voting",
        }

        # Add all individual votes
        for name, vote_val in zip(self.names, self.votes):
            vote.vote(vote_dictionary[vote_val], name)
        return vote


class HouseRollCall(PdfPage):
    def process_page(self):
        # Each bill vote starts with the same text, so use it as a separator.
        separator = "MASSACHUSETTS HOUSE OF REPRESENTATIVES"

        # Ignore first element after split because it's going to be blank
        vote_text = self.text.split(separator)[1:]

        for vote in vote_text:
            vote_parser = HouseVoteRecordParser(vote)
            if (warning := vote_parser.get_warning()) is not None:
                self.logger.warn(warning)
            else:
                vote_parser.error_if_invalid()
                vote_event = vote_parser.createVoteEvent()
                vote_event.add_source(self.source.url, note="Vote record pdf")
                yield vote_event


"""

"""
