import os
import re
from urllib import parse as urlparse
import datetime
import scrapelib
import collections

import lxml.html
from openstates.scrape import Scraper, VoteEvent


def next_tag(el):
    """
    Return next tag, skipping <br>s.
    """
    el = el.getnext()
    while el.tag == "br":
        el = el.getnext()
    return el


def clean_journal(root, logger):
    # Remove page breaks
    for el in root.xpath("//hr[@noshade and @size=1]"):
        parent = el.getparent()
        previous = el.getprevious()
        if previous:
            parent.remove(previous)
        logger.debug(f"Killed hr: {el.text_content()}")
        parent.remove(el)

    # Does lxml not support xpath ends-with?
    for el in root.xpath("//p[contains(text(), 'REGULAR SESSION')]"):
        if el.text.endswith("REGULAR SESSION"):
            parent = el.getparent()
            logger.debug(f"Killed REGULAR SESSION: {el.text_content()}")
            parent.remove(el)

    for el in root.xpath("//p[contains(text(), 'JOURNAL')]"):
        if (
            "HOUSE JOURNAL" in el.text or "SENATE JOURNAL" in el.text
        ) and "Day" in el.text:
            parent = el.getparent()
            logger.debug(f"Killed HOUSE/SENATE/JOURNAL: {el.text_content()}")
            parent.remove(el)

    # Remove empty paragraphs
    for el in root.xpath("//p[not(node())]"):
        if el.tail and el.tail != "\r\n" and el.getprevious() is not None:
            el.getprevious().tail = el.tail
        logger.debug(f"Killed empty para: {el.text_content()}")
        el.getparent().remove(el)

    # Journal pages sometimes replace spaces with <font color="White">i</font>
    # (or multiple i's for bigger spaces)
    for el in root.xpath('//font[@color="White"]'):
        if el.text:
            logger.debug("Replaced white text")
            el.text = " " * len(el.text)


def names(el):
    text = (el.text or "") + (el.tail or "")
    split_name_list = text.split(";")
    if len(split_name_list) < 7:
        # probably failed to properly split on semi-colons; try commas:
        split_name_list = text.split(",")

    names = []
    for name in split_name_list:
        name = name.strip().replace("\r\n", "").replace("  ", " ")

        if not name:
            continue

        name = clean_name_special_cases(name)

        if ";" in name:
            names_still_with_semicolon = name.split(";")
            for n in names_still_with_semicolon:
                n = n.strip().replace(".", "")
                if " — " in n:
                    n = n.split()[-1]
                names.append(n)
        else:
            names.append(name)

    if names:
        # First item in the list will have stuff to ignore before an mdash
        names[0] = clean_starting_name(names[0]).strip()
        # Get rid of trailing '.'
        names[-1] = names[-1][0:-1]

    return names


def clean_name_special_cases(name):
    if name == "Gonzalez Toureilles":
        name = "Toureilles"
    elif name == "Mallory Caraway":
        name = "Caraway"
    elif name == "Martinez Fischer":
        name = "Fischer"
    elif name == "Rios Ybarra":
        name = "Ybarra"
    return name


def clean_starting_name(name):
    return re.split(r"[\u2014:]", name)[-1]


def votes(root, session, chamber):
    for vote in record_votes_with_yeas(root, session, chamber):
        yield vote
    for vote in viva_voce_votes(root, session, chamber):
        yield vote
    for vote in record_votes_with_short_count_notation(root, session, chamber):
        yield vote


def first_int(res):
    if res is not None:
        return int(next(group for group in res.groups() if group is not None))


def identify_classification(motion_text: str, passed: bool) -> list[str]:
    classifications = []
    if passed is True:
        classifications.append("passage")
    if "third reading" in motion_text.lower():
        classifications.append("reading-3")

    return classifications


class BaseVote(object):
    def __init__(self, el):
        self.el = el

    @property
    def text(self):
        return self.el.text_content()

    @property
    def previous(self):
        return self.el.getprevious().getprevious()

    @property
    def next(self):
        return self.el.getnext().getnext()

    @property
    def is_valid(self):
        return self.bill_id is not None and self.chamber is not None

    @property
    def bill_id(self):
        bill_id = get_bill(self.el) or get_bill(self.previous)
        return clean_bill_id(bill_id)

    @property
    def chamber(self):
        bill_id = self.bill_id or ""
        # bill identifiers can start with CS or CH, and there are several variants
        # these seem to be committee substitutes/reports on existing bills
        if bill_id.startswith("H") or bill_id.startswith("CSH"):
            return "lower"
        if bill_id.startswith("S") or bill_id.startswith("CSS"):
            return "upper"


# Note: Vote count patterns are inconsistent across journals and may follow the pattern
# "145 Yeas, 0 Nays" (https://journals.house.texas.gov/HJRNL/85R/HTML/85RDAY02FINAL.HTM) or
# "Yeas 20, Nays 10" (https://journals.senate.texas.gov/SJRNL/85R/HTML/85RSJ02-08-F.HTM)
class MaybeVote(BaseVote):
    yeas_pattern = re.compile(r"yeas[\s\xa0]+(\d+)|(\d+)[\s\xa0]+yeas", re.IGNORECASE)
    nays_pattern = re.compile(r"nays[\s\xa0]+(\d+)|(\d+)[\s\xa0]+nays", re.IGNORECASE)
    present_pattern = re.compile(
        r"present[\s\xa0]+(\d+)|(\d+)[\s\xa0]+present", re.IGNORECASE
    )
    record_pattern = re.compile(r"\(record[\s\xa0]+(\d+)\)", re.IGNORECASE)
    passed_pattern = re.compile(r"(adopted|passed|prevailed)", re.IGNORECASE)
    check_prev_pattern = re.compile(r"the (motion|resolution)", re.IGNORECASE)
    votes_pattern = re.compile(r"^(yeas|nays|present|absent)", re.IGNORECASE)
    amendment_pattern = re.compile(r"the amendment to", re.IGNORECASE)
    motion_text_pattern = re.compile(r"moved that (.+)$", re.IGNORECASE)

    @property
    def is_valid(self):
        return (
            super(MaybeVote, self).is_valid
            and self.yeas is not None
            and self.nays is not None
        )

    @property
    def is_amendment(self):
        return self.amendment_pattern.search(self.text) is not None

    @property
    def passed(self):
        passed_match = self.passed_pattern.search(self.text)
        if passed_match:
            return bool(passed_match)
        elif self.yeas > 0 or self.nays > 0:
            return self.yeas > self.nays
        else:
            return False

    @property
    def yeas(self):
        res = self.yeas_pattern.search(self.text)
        return first_int(res)

    @property
    def nays(self):
        res = self.nays_pattern.search(self.text)
        return first_int(res)

    @property
    def present(self):
        res = self.present_pattern.search(self.text)
        return first_int(res)

    @property
    def record(self):
        res = self.record_pattern.search(self.text)
        return first_int(res)

    @property
    def votes(self):
        votes = collections.defaultdict(list)
        el = next_tag(self.el)
        while el.text:
            res = re.match(self.votes_pattern, el.text)
            if not res:
                break
            votes[res.groups()[0].lower()].extend(names(el))
            el = next_tag(el)
        return votes

    @property
    def motion_text(self):
        previous_text = self.previous.text_content()
        match = self.motion_text_pattern.search(previous_text)
        if match:
            return match.groups()[0]
        else:
            return None


# Some votes are recorded as voice votes
class MaybeViva(BaseVote):
    amendment_pattern = re.compile(r"the amendment to", re.IGNORECASE)
    floor_amendment_pattern = re.compile(r"floor amendment no", re.IGNORECASE)
    passed_pattern = re.compile(
        r"(all members are deemed to have voted \"yea\"|adopted|passed|prevailed)",
        re.IGNORECASE,
    )
    viva_voce_pattern = re.compile(r"viva voce vote", re.IGNORECASE)
    motion_pattern = re.compile(r"on the (.+) except as follows", re.IGNORECASE)

    @property
    def is_valid(self):
        return (
            super(MaybeViva, self).is_valid
            and self.viva_voce_pattern.search(self.previous.text_content()) is not None
        )

    @property
    def is_amendment(self):
        return bool(
            self.amendment_pattern.search(self.previous.text_content())
            or self.floor_amendment_pattern.search(self.text)
        )

    @property
    def passed(self):
        return bool(self.passed_pattern.search(self.text))

    @property
    def motion_text(self):
        match = self.motion_pattern.search(self.text)
        if match:
            return match.groups()[0]
        else:
            return None


# Some votes are recorded in a terse vote count notation
# seems to be the case when the opposite chamber passes a bunch of bills?
# see record_votes_with_short_count_notation() for examples of ShortCount vote text
class MaybeShortCount(BaseVote):

    nay_votes_pattern = re.compile(r"\(([^)]+)\s+-\s+no\)", re.IGNORECASE)
    nay_vote_request_pattern = re.compile(
        r"\(([^)]+)\s+requested to be recorded voting no", re.IGNORECASE
    )

    @property
    def is_valid(self):
        return (
            super(MaybeShortCount, self).is_valid
            and self.counts["yeas"] is not None
            and self.counts["nays"] is not None
        )

    @property
    def counts(self):
        match = short_count_notation_regex.search(self.text)
        if match:
            return {
                "yeas": int(match.groups()[0]),
                "nays": int(match.groups()[1]),
                "other": int(match.groups()[2]),
            }
        else:
            return {
                "yeas": None,
                "nays": None,
                "other": None,
            }

    @property
    def passed(self):
        return self.counts["yeas"] > self.counts["nays"]

    @property
    def votes(self):
        # short notation seems to assume everyone is voting yes
        # and only makes note of those voting no
        no_voter_names = []
        no_match = self.nay_votes_pattern.search(self.text)
        if no_match:
            name_list = re.sub(r",?\sand\s", ", ", no_match.groups()[0])
            no_voter_names.extend(name_list.split(", "))
        no_requested_later_match = self.nay_vote_request_pattern.search(self.text)
        if no_requested_later_match:
            name_list = re.sub(r",?\sand\s", ", ", no_requested_later_match.groups()[0])
            no_voter_names.extend(name_list.split(", "))
        return {"nays": no_voter_names}


def get_bill(el):
    # allow for bill numbers like HB, SB, HR, SR, HJR, SJR, SCR followed by digits
    # \s space character is used because there are some non-space whitespaces
    b = re.findall(r"[HS][JC]?[BR]\s+\d+", el.text_content())
    if b:
        return b[0]


def clean_bill_id(bill_id):
    if bill_id:
        bill_id = bill_id.replace("\xa0", " ")
        bill_id = re.sub(r"CS(SB|HB)", r"\1", bill_id)
        bill_id = bill_id.split(" - ")[0]  # clean off things like " - continued"
    return bill_id


short_count_notation_regex = re.compile(
    r"\((\d+)\s+-\s+(\d+)\s+-\s+(\d+)\)", re.IGNORECASE
)


def record_votes_with_short_count_notation(root, session, chamber):
    # votes with short vote count notation may look like:
    # SB 422 (Cook, Patterson, and Thimesch - no) (135 - 3 - 1)
    # or
    # SB 2479 (Ashby, Buckley, Bumgarner, Cain, Clardy, Darby, Gates, Gerdes, C.E. Harris, C.J. Harris, Hefner,
    # Holland, Hull, Lambert, Leach, Metcalf, Patterson, Schatzline, Shaheen, Shine, Slawson, Smith, Tinderholt,
    # Toth, Troxclair, Vasut, and Wilson - no) (111 - 27 - 1) (Harrison and Isaac requested to be recorded
    # voting no after the deadline established by Rule 5, Section 52, of the House Rules.)

    # so we catch them by finding the (135 - 3 - 1) notation
    paragraphs = root.xpath('//div[@class = "textpara"]')
    vote_elements = []
    for p in paragraphs:
        if short_count_notation_regex.search(p.text_content()):
            vote_elements.append(p)

    maybe_votes = [MaybeShortCount(el) for el in vote_elements]

    for mv in maybe_votes:
        if not mv.is_valid:
            continue

        if mv.passed:
            motion_text = "passage"
        else:
            motion_text = "other"

        v = VoteEvent(
            chamber=chamber,
            start_date=None,
            motion_text=motion_text,
            result="pass" if mv.passed else "fail",
            classification=identify_classification(motion_text, mv.passed),
            legislative_session=session,
            bill=mv.bill_id,
            bill_chamber=mv.chamber,
        )

        v.set_count("yes", mv.counts["yeas"] or 0)
        v.set_count("no", mv.counts["nays"] or 0)
        v.set_count("other", mv.counts["other"] or 0)

        # these votes only seem to list explicit voters who vote no
        for each in mv.votes["nays"]:
            each = clean_vote_name(each)
            v.no(each)

        yield v


def record_votes_with_yeas(root, session, chamber):
    # votes with "yeas" may look like:
    # SB 186 was passed by (Record 2040): 122 Yeas, 17 Nays, 1 Present, not voting.
    # or
    # SJR 35 failed of adoption (not receiving the necessary two-thirds vote) by (Record 2041): 88 Yeas, 0 Nays, 54
    # Present, not voting.
    # or
    # Amendment No. 1 failed of adoption by (Record 2044): 48 Yeas, 78 Nays, 1 Present, not voting
    vote_selectors = [
        '[@class = "textpara"]',
        '[contains(translate(., "YEAS", "yeas"), "yeas")]',
    ]
    vote_elements = root.xpath("//div{}".format("".join(vote_selectors)))
    maybe_votes = [MaybeVote(el) for el in vote_elements]

    for mv in maybe_votes:
        if not mv.is_valid:
            continue

        if mv.motion_text:
            motion_text = mv.motion_text
        elif mv.passed:
            motion_text = "passage"
        else:
            motion_text = "other"

        v = VoteEvent(
            chamber=chamber,
            start_date=None,
            motion_text=motion_text,
            result="pass" if mv.passed else "fail",
            classification=identify_classification(motion_text, mv.passed),
            legislative_session=session,
            bill=mv.bill_id,
            bill_chamber=mv.chamber,
        )

        v.set_count("yes", mv.yeas or 0)
        v.set_count("no", mv.nays or 0)
        v.set_count("not voting", mv.present or 0)

        for each in mv.votes["yeas"]:
            each = clean_vote_name(each)
            v.yes(each)
        for each in mv.votes["nays"]:
            each = clean_vote_name(each)
            v.no(each)
        for each in mv.votes["present"]:
            each = clean_vote_name(each)
            v.vote("not voting", each)
        for each in mv.votes["absent"]:
            each = clean_vote_name(each)
            v.vote("absent", each)

        yield v


def clean_vote_name(name):
    # Removes extra text like Committee Meeting —  and Excused —
    if " — " in name:
        name = " ".join(name.split(" — ")[1:])
    return name


def viva_voce_votes(root, session, chamber):
    vote_elements = root.xpath('//div[starts-with(., "All Members are deemed")]')
    maybe_votes = [MaybeViva(el) for el in vote_elements]

    for mv in maybe_votes:
        if not mv.is_valid:
            continue

        if mv.motion_text:
            motion_text = mv.motion_text
        elif mv.passed:
            motion_text = "passage"
        else:
            motion_text = "other"

        v = VoteEvent(
            chamber=chamber,
            start_date=None,
            motion_text=motion_text,
            result="pass" if mv.passed else "fail",
            classification=identify_classification(motion_text, mv.passed),
            legislative_session=session,
            bill=mv.bill_id,
            bill_chamber=mv.chamber,
        )

        v.set_count("yes", 0)
        v.set_count("no", 0)
        v.set_count("absent", 0)
        v.set_count("not voting", 0)

        yield v


class TXVoteScraper(Scraper):
    def scrape(self, session=None, chamber=None, url_match=None):
        if session == "821":
            self.warning("no journals for session 821")
            return

        if len(session) == 2:
            session = "%sR" % session

        chambers = [chamber] if chamber else ["upper", "lower"]

        # go through every day this year before today
        # (or end of the year of the session, if prior year)
        # and see if there were any journals that day
        today = datetime.datetime.today()
        session_year = self.get_session_year(session)
        if session_year != today.year:
            today = today.replace(year=session_year, month=12, day=31)
        today = datetime.datetime(today.year, today.month, today.day)
        journal_day = datetime.datetime(today.year, 1, 1)
        day_num = 1
        urls_scraped = []
        urls_failed_on_exception = []
        while journal_day <= today:
            if "lower" in chambers:
                journal_root = (
                    "https://journals.house.texas.gov/HJRNL/%s/HTML/" % session
                )
                journal_url = (
                    journal_root + session + "DAY" + str(day_num).zfill(2) + "FINAL.HTM"
                )
                if url_match is None or url_match.lower() in journal_url.lower():
                    try:
                        self.get(journal_url)
                    except scrapelib.HTTPError:
                        urls_failed_on_exception.append(journal_url)
                        pass
                    else:
                        urls_scraped.append(journal_url)
                        yield from self.scrape_journal(journal_url, "lower", session)

                # Check if this "legislative day" has a Continuing journal entry
                # a "Cont" entry can occur the next actual calendar day
                continuing_url = journal_url.replace("FINAL", "CFINAL")
                if url_match is None or url_match.lower() in continuing_url.lower():
                    try:
                        self.get(continuing_url)
                    except scrapelib.HTTPError:
                        urls_failed_on_exception.append(continuing_url)
                        pass
                    else:
                        urls_scraped.append(continuing_url)
                        yield from self.scrape_journal(continuing_url, "lower", session)

            if "upper" in chambers:
                journal_root = (
                    "https://journals.senate.texas.gov/SJRNL/%s/HTML/" % session
                )
                journal_url = journal_root + "%sSJ%s-%s-F.HTM" % (
                    session,
                    str(journal_day.month).zfill(2),
                    str(journal_day.day).zfill(2),
                )
                if url_match is None or url_match.lower() in journal_url.lower():
                    try:
                        self.get(journal_url)
                    except scrapelib.HTTPError:
                        urls_failed_on_exception.append(journal_url)
                        pass
                    else:
                        urls_scraped.append(journal_url)
                        yield from self.scrape_journal(journal_url, "upper", session)

                # Check if this "legislative day" has a Continuing journal entry
                # a "Cont" entry can occur the next actual calendar day
                continuing_url = journal_url.replace("F.", "F1.")
                if url_match is None or url_match.lower() in continuing_url.lower():
                    try:
                        self.get(continuing_url)
                    except scrapelib.HTTPError:
                        urls_failed_on_exception.append(continuing_url)
                        pass
                    else:
                        urls_scraped.append(continuing_url)
                        yield from self.scrape_journal(continuing_url, "upper", session)

            journal_day += datetime.timedelta(days=1)
            day_num += 1

        urls_tried = "\n".join(urls_scraped)
        urls_failed_on_exception = "\n".join(urls_failed_on_exception)
        # log out URLs that were either scraped or failed out (ignored)
        # useful if you want to ensure a certain URL is getting tried
        self.logger.debug(f"Scraped urls: {urls_tried}")
        self.logger.debug(f"Failed urls: {urls_failed_on_exception}")

    def scrape_journal(self, url, chamber, session):
        page = self.get(url).text

        root = lxml.html.fromstring(page)
        clean_journal(root, self.logger)

        if chamber == "lower":
            div = root.xpath("//div[@class = 'textpara']")[0]
            date_str = " ".join(div.text.split()[-4:]).strip()
            date = datetime.datetime.strptime(date_str, "%A, %B %d, %Y").date()
        else:
            year = self.get_session_year(session)
            if year is None:
                return
            fname = os.path.split(urlparse.urlparse(url).path)[-1]
            date_str = (
                re.match(r"%sSJ(\d\d-\d\d).*\.HTM" % session, fname).group(1)
                + " %s" % year
            )
            date = datetime.datetime.strptime(date_str, "%m-%d %Y").date()

        for vn, vote in enumerate(votes(root, session, chamber)):
            vote.start_date = date
            vote.add_source(url)

            # no good identifier on votes, so we'll try this.
            # vote pages in journal shouldn't change so ordering should be OK
            # but might cause an issue if they do change a journal page
            vote.dedupe_key = "{}#{}".format(url, vn)
            yield vote

    def get_session_year(self, session):
        session_instance = next(
            (
                s
                for s in self.jurisdiction.legislative_sessions
                if s["identifier"] == session or s["identifier"] == session.strip("R")
            ),
            None,
        )

        if session_instance is None:
            self.warning("Session metadata could not be found for %s", session)
            return None
        year = datetime.datetime.strptime(
            session_instance["start_date"], "%Y-%m-%d"
        ).year
        return year
