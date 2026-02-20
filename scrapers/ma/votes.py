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
        yield from HouseJournalDirectory(session=session).do_scrape()
        yield from SenateJournalDirectory(session=session).do_scrape()


class HouseJournalDirectory(HtmlPage):
    source = URL("https://malegislature.gov/Journal/House/", verify=False)

    def __init__(self, source=None, session=None):
        super().__init__(source=source or self.source)
        self.session = session

    def process_page(self):
        # find all links to a file called RollCalls
        # One of these files exists for each year directory
        roll_calls = [
            x for x in XPath("//a/@href").match(self.root) if x.endswith("RollCalls")
        ]
        for rc in roll_calls:
            vote_events = HouseRollCall(
                source=URL(rc, verify=False), session=self.session
            ).do_scrape()
            for vote_event in vote_events:
                vote_event.add_source(self.source.url, note="House journal listing")
                yield vote_event


class SenateJournalDirectory(HtmlListPage):
    source = URL("https://malegislature.gov/Journal/Senate", verify=False)
    votes_list = []

    def __init__(self, source=None, session=None):
        super().__init__(source=source or self.source)
        self.session = session

    def process_page(self):
        # Find all link to each month
        month_links = XPath("//a[@aria-controls='journalList']/@href").match(self.root)
        for month_link in month_links:
            vote_events = SenateJournalMonth(
                source=URL(month_link, verify=False),
                votes_list=self.votes_list,
                session=self.session,
            ).do_scrape()
            for vote_event in vote_events:
                # vote_event.add_source(self.source.url, note="Senate jouenal listing")
                yield vote_event


class SenateJournalMonth(HtmlListPage):
    def __init__(self, source, votes_list, session=None):
        super().__init__(source=source)
        self.votes_list = votes_list
        self.session = session

    def process_page(self):
        journal_pdf_links = XPath("//tr/td/a/@href").match(self.root)
        for journal_pdf_link in journal_pdf_links:
            # if journal_pdf_link in (
            #     "https://malegislature.gov/Journal/Senate/193/806/sj03302023_1100AM.pdf",
            #     "https://malegislature.gov/Journal/Senate/193/768/sj03232023_0100PM.pdf",
            # ):
            yield SenateJournal(
                source=URL(journal_pdf_link, verify=False),
                votes_list=self.votes_list,
                session=self.session,
            )


class SenateJournal(PdfPage):
    motion_and_vote_total = r"((?P<rawmotion>.{900}))\(yeas\s*(?P<firstyeatotal>\d+)\s*(?:-|to)\s*nays.(?P<firstnaytotal>\d+)\)"
    vote_id = r"\[Yeas\.?.and.Nays\.?.No\.?.(?P<votenumber>\d+)\]"
    vote_section = r"YEAS(?P<yealines>.*?)(?P<secondyeatotal>\d+)\.(?P<extrayealines>.*?)NAYS(?P<naylines>.*?)(?P<secondnaytotal>\d+)(?:(?P<extranaylines>.{0,30}?)ABSENT OR NOT VOTING(?P<nvlines>.*?)(?P<secondnvtotal>\d+))?"

    motion_and_vote_total_re = re.compile(motion_and_vote_total, re.DOTALL)
    vote_id_re = re.compile(vote_id, re.DOTALL)
    vote_section_re = re.compile(vote_section, re.DOTALL)

    total_vote_re = re.compile(
        f"{motion_and_vote_total}.*?{vote_id}.*?{vote_section}", re.DOTALL
    )

    not_name_re = re.compile(
        r"^(\d|UNCORRECTED|Joint Rules|\.|Real ID,-- homeless"
        r"|Pharmacists,-- PrEP\."
        r"|Brewster,-- land\."
        r"|Provincetown,-wastewater"
        r")"
    )

    precise_motion = r"question on\s+(.+)\s+was determined"
    precise_motion_re = re.compile(precise_motion, re.DOTALL)

    bill_id = r"(House|Senate),\s+No\.\s+(\d+)"
    bill_id_re = re.compile(bill_id, re.DOTALL)

    motion_classification = {
        r"passing.+engross": "passage",
        r"adoption.+amendment": "amendment",
        r"passing.+enacted": "passage",
        r"approving.+plan": "passage",
    }

    date_time_re = re.compile(r"sj(\d{8})_")

    text = None
    journal_date = None
    bill_id = None
    vote_date = None

    def __init__(self, source, votes_list, session=None):
        super().__init__(source=source)
        self.votes_list = votes_list
        self.session = session

    def process_date(self):
        # Find the match
        datetime_match = self.date_time_re.search(self.source.url)

        if datetime_match:
            date_str = datetime_match.group(1)
            vote_date = dt.datetime.strptime(date_str, "%m%d%Y")
            formatted_date = vote_date.strftime("%Y-%m-%d")

            return formatted_date

        else:
            raise Exception(
                f"Datetime with known format not in pdf url: {self.source.url}"
            )

    def process_page(self):
        self.vote_date = self.process_date()

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
            self.logger.warn(
                f"\nCould not accurately parse votes for "
                f"{self.source.url}\n"
                f"len(votes_mt):{len(votes_mt)}\n"
                f"len(votes_s):{len(votes_s)}\n"
                f"len(votes_id):{len(votes_id)}\n"
            )
        else:
            # Run full regex search.
            vote_matches = self.total_vote_re.finditer(self.text)
            votes_data_list = []

            i = 0
            for v_match in vote_matches:
                vote = self.parse_match(v_match, i)
                votes_data_list.append(vote)
                i += 1
                yield vote

    def parse_match(self, match, index):
        bill_id = self.get_bill_id(index)
        if not bill_id:
            self.logger.warn(
                f"No valid bill id found preceding vote lines in {self.source.url}"
            )
            return {}

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

        motion_text = self.precise_motion_re.search(raw_motion_text)
        if motion_text:
            motion_text = motion_text.group(1)
        else:
            self.logger.warn(
                f"No valid motion text found preceding vote lines in {self.source}"
            )
            return
        single_line_motion = motion_text.replace("\n", " ")

        normalized_motion = single_line_motion.capitalize()

        vote_classification = None
        for pattern, classification in self.motion_classification.items():
            if re.compile(pattern).search(single_line_motion):
                vote_classification = classification
                break

        if not vote_classification:
            self.logger.warn(
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

        # vote_number = match.group("votenumber")

        # Get list of voter names for each section
        yea_voters = self.find_names(match.group("yealines"))
        nay_voters = self.find_names(match.group("naylines"))
        yea_voters.extend(self.find_names(match.group("extrayealines")))

        # extre nay lines section may be missing
        possible_extra_nay_voters = match.group("extranaylines")
        if possible_extra_nay_voters is None:
            possible_extra_nay_voters = ""
        nay_voters.extend(self.find_names(possible_extra_nay_voters))

        # # non-voting voter name section may be missing
        # possible_nv_voters = match.group("nvlines")
        # if possible_nv_voters is None:
        #     possible_nv_voters = ""
        # nv_voters = self.find_names(possible_nv_voters)

        # # To help flag certain high priority console logging during debugging
        # red_color = '\033[91m'
        # reset_color = '\033[0m'

        first_margin = first_total_yea - first_total_nay
        final_margin = total_yea - total_nay
        abs_first, abs_final = abs(first_margin), abs(final_margin)
        if abs_first < abs_final:
            determinative_margin = abs_first
            vote_passed = True if first_margin > 0 else False
        else:
            determinative_margin = abs_final
            vote_passed = True if final_margin > 0 else False

        yea_mismatch = first_total_yea != total_yea
        nay_mismatch = first_total_nay != total_nay
        if yea_mismatch or nay_mismatch:
            self.logger.warn(
                f"Cannot accurately parse to determine margins for vote {index + 1} in {self.source.url}"
            )
            return {}

        # # Check that total voters and total votes match up
        yea_matches_miscount = len(yea_voters) - total_yea
        nay_matches_miscount = len(nay_voters) - total_nay
        for miscount in yea_matches_miscount, nay_matches_miscount:
            # Allows for minor miscount in cases of PDF formatting issues
            if abs(miscount) > determinative_margin:
                self.logger.warn(
                    f"Cannot accurately parse to determine margins for vote {index + 1} in {self.source.url}"
                )
                return {}

        vote_event = VoteEvent(
            chamber="upper",
            legislative_session=self.session,
            start_date=self.vote_date,
            motion_text=normalized_motion,
            bill=bill_id,
            result="pass" if vote_passed else "fail",
            classification=vote_classification,
        )

        vote_event.add_source(self.source.url)

        return vote_event

    # Finds names in text, ignoring some common phrases and empty lines
    def find_names(self, text):
        text = [x.strip() for x in text.split("\n")]
        text = [x for x in text if x != ""]
        names = [x for x in text if not self.not_name_re.match(x) and "," in x]

        return names

    def get_bill_id(self, index):
        pre_vote_sections = self.text.split("(yeas")[:-1]
        relevant_section = pre_vote_sections[index]
        bill_id_match = re.findall(self.bill_id_re, relevant_section)
        if bill_id_match:
            chamber, number = bill_id_match[-1]
            self.bill_id = f"{chamber[0]} {number}"
        if not self.bill_id:
            self.logger.warn(
                f"No preceding bill id for vote {index + 1} in {self.source.url}"
            )
        return self.bill_id


class HouseVoteRecordParser:
    tz = pytz.timezone("US/Eastern")
    total_yea_re = re.compile(r"(\d+) yeas", re.IGNORECASE)
    total_nay_re = re.compile(r"(\d+) nays", re.IGNORECASE)
    total_nv_re = re.compile(r"(\d+) n/v", re.IGNORECASE)
    bill_re = re.compile(r"(h|s)\.? ?(\d+) ?(.*)", re.IGNORECASE)
    number_re = re.compile(r"no\.? ?(\d+)", re.IGNORECASE)

    def __init__(self, vote_text, session=None):
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
        self.session = session
        lines = vote_text.split("\n")
        self.raw = vote_text
        for line in lines:
            if re.search(r"^[XP]\s", line):
                sub_lines = line.split(" ")
                self.read_line(sub_lines[0])
                self.read_line(sub_lines[1])
            else:
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
            when = dt.datetime.strptime(line, "%m/%d/%Y %I:%M %p")
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
            legislative_session=self.session,
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
    def __init__(self, source, session=None):
        super().__init__(source=source)
        self.session = session

    def process_page(self):
        # Each bill vote starts with the same text, so use it as a separator.
        separator = "MASSACHUSETTS HOUSE OF REPRESENTATIVES"

        # Ignore first element after split because it's going to be blank
        vote_text = self.text.split(separator)[1:]

        for vote in vote_text:
            vote_parser = HouseVoteRecordParser(vote, session=self.session)
            if (warning := vote_parser.get_warning()) is not None:
                self.logger.warn(warning)
            else:
                vote_parser.error_if_invalid()
                vote_event = vote_parser.createVoteEvent()
                vote_event.add_source(self.source.url, note="Vote record pdf")
                yield vote_event
