import os
import re
from urllib import parse as urlparse
import datetime
import scrapelib
import collections

import lxml.html
from openstates_core.scrape import Scraper, VoteEvent


def next_tag(el):
    """
    Return next tag, skipping <br>s.
    """
    el = el.getnext()
    while el.tag == "br":
        el = el.getnext()
    return el


def clean_journal(root):
    # Remove page breaks
    for el in root.xpath("//hr[@noshade and @size=1]"):
        parent = el.getparent()
        previous = el.getprevious()
        if previous:
            parent.remove(previous)
        parent.remove(el)

    # Does lxml not support xpath ends-with?
    for el in root.xpath("//p[contains(text(), 'REGULAR SESSION')]"):
        if el.text.endswith("REGULAR SESSION"):
            parent = el.getparent()
            parent.remove(el)

    for el in root.xpath("//p[contains(text(), 'JOURNAL')]"):
        if (
            "HOUSE JOURNAL" in el.text or "SENATE JOURNAL" in el.text
        ) and "Day" in el.text:
            parent = el.getparent()
            parent.remove(el)

    # Remove empty paragraphs
    for el in root.xpath("//p[not(node())]"):
        if el.tail and el.tail != "\r\n" and el.getprevious() is not None:
            el.getprevious().tail = el.tail
        el.getparent().remove(el)

    # Journal pages sometimes replace spaces with <font color="White">i</font>
    # (or multiple i's for bigger spaces)
    for el in root.xpath('//font[@color="White"]'):
        if el.text:
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
    for vote in record_votes(root, session, chamber):
        yield vote
    for vote in viva_voce_votes(root, session, chamber):
        yield vote


def first_int(res):
    if res is not None:
        return int(next(group for group in res.groups() if group is not None))


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
        if bill_id.startswith("H") or bill_id.startswith("CSHB"):
            return "lower"
        if bill_id.startswith("S") or bill_id.startswith("CSSB"):
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
        return bool(self.passed_pattern.search(self.text))

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


class MaybeViva(BaseVote):
    amendment_pattern = re.compile(r"the amendment to", re.IGNORECASE)
    floor_amendment_pattern = re.compile(r"floor amendment no", re.IGNORECASE)
    passed_pattern = re.compile(r"(adopted|passed|prevailed)", re.IGNORECASE)
    viva_voce_pattern = re.compile(r"viva voce vote", re.IGNORECASE)

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


def get_bill(el):
    b = re.findall(r"[HS][BR] \d+", el.text_content())
    if b:
        return b[0]


def clean_bill_id(bill_id):
    if bill_id:
        bill_id = bill_id.replace(u"\xa0", " ")
        bill_id = re.sub(r"CS(SB|HB)", r"\1", bill_id)
        bill_id = bill_id.split(" - ")[0]  # clean off things like " - continued"
    return bill_id


vote_selectors = [
    '[@class = "textpara"]',
    '[contains(translate(., "YEAS", "yeas"), "yeas")]',
]


def record_votes(root, session, chamber):
    for el in root.xpath("//div{}".format("".join(vote_selectors))):
        mv = MaybeVote(el)
        if not mv.is_valid:
            continue

        v = VoteEvent(
            chamber=chamber,
            start_date=None,
            motion_text="passage" if mv.passed else "other",
            result="pass" if mv.passed else "fail",
            classification="passage" if mv.passed else "other",
            legislative_session=session[0:2],
            bill=mv.bill_id,
            bill_chamber=mv.chamber,
        )

        v.set_count("yes", mv.yeas or 0)
        v.set_count("no", mv.nays or 0)
        v.set_count("not voting", mv.present or 0)

        for each in mv.votes["yeas"]:
            v.yes(each)
        for each in mv.votes["nays"]:
            v.no(each)
        for each in mv.votes["present"]:
            v.vote("not voting", each)
        for each in mv.votes["absent"]:
            v.vote("absent", each)

        yield v


def viva_voce_votes(root, session, chamber):
    for el in root.xpath(u'//div[starts-with(., "All Members are deemed")]'):
        mv = MaybeViva(el)
        if not mv.is_valid:
            continue

        v = VoteEvent(
            chamber=chamber,
            start_date=None,
            motion_text="passage" if mv.passed else "other",
            result="pass" if mv.passed else "fail",
            classification="passage" if mv.passed else "other",
            legislative_session=session[0:2],
            bill=mv.bill_id,
            bill_chamber=mv.chamber,
        )

        v.set_count("yes", 0)
        v.set_count("no", 0)
        v.set_count("absent", 0)
        v.set_count("not voting", 0)

        yield v


class TXVoteScraper(Scraper):
    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("No session specified; using %s", session)

        if session == "821":
            self.warning("no journals for session 821")
            return

        if len(session) == 2:
            session = "%sR" % session

        chambers = [chamber] if chamber else ["upper", "lower"]

        # go through every day this year before today
        # and see if there were any journals that day
        today = datetime.datetime.today()
        today = datetime.datetime(today.year, today.month, today.day)
        journal_day = datetime.datetime(today.year, 1, 1)
        day_num = 1
        while journal_day <= today:
            if "lower" in chambers:
                journal_root = (
                    "https://journals.house.texas.gov/HJRNL/%s/HTML/" % session
                )
                journal_url = (
                    journal_root + session + "DAY" + str(day_num).zfill(2) + "FINAL.HTM"
                )
                try:
                    self.get(journal_url)
                except scrapelib.HTTPError:
                    pass
                else:
                    yield from self.scrape_journal(journal_url, "lower", session)

            if "upper" in chambers:
                journal_root = (
                    "https://journals.senate.texas.gov/SJRNL/%s/HTML/" % session
                )
                journal_url = journal_root + "%sSJ%s-%s-F.HTM" % (
                    session,
                    str(journal_day.month).zfill(2),
                    str(journal_day.day).zfill(2),
                )
                try:
                    self.get(journal_url)
                except scrapelib.HTTPError:
                    pass
                else:
                    yield from self.scrape_journal(journal_url, "upper", session)

            journal_day += datetime.timedelta(days=1)
            day_num += 1

    def scrape_journal(self, url, chamber, session):
        page = self.get(url).text

        root = lxml.html.fromstring(page)
        clean_journal(root)

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
            vote.pupa_id = "{}#{}".format(url, vn)
            yield vote

    def get_session_year(self, session):
        if "R" in session:
            session_num = session.strip("R")
        else:
            session_num = session
        session_instance = next(
            (
                s
                for s in self.jurisdiction.legislative_sessions
                if s["identifier"] == session_num
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
