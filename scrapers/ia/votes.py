# -*- coding: utf8 -*-
from datetime import datetime, time, timezone, timedelta
import re
import collections
import lxml.etree

from openstates.utils import convert_pdf
from openstates.scrape import Scraper, VoteEvent


SITE_IDS = {
    "2021-2022": "89",
    "2019-2020": "88",
    "2017-2018": "87",
    "2015-2016": "86",
    "2013-2014": "85",
    "2011-2012": "84",
}


class IAVoteScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if chamber:
            yield from self.scrape_chamber(chamber, session)
        else:
            yield from self.scrape_chamber("upper", session)
            yield from self.scrape_chamber("lower", session)

    def scrape_chamber(self, chamber, session):
        # Each PDF index page contains just one year, not a whole session
        # Therefore, we need to iterate over both years in the session
        session_id = SITE_IDS[session]
        for sub_session in [1, 2]:
            url = "https://www.legis.iowa.gov/legislation/journals/{}".format(
                "house" if chamber == "lower" else "senate"
            )
            params = {"ga": session_id, "session": sub_session}
            html = self.get(url, params=params).content

            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            urls = [x for x in doc.xpath("//a[@href]/@href") if x.endswith(".pdf")][
                ::-1
            ]

            for url in urls:
                _, filename = url.rsplit("/", 1)
                journal_template = "%Y%m%d_{}.pdf"
                try:
                    if chamber == "upper":
                        journal_format = journal_template.format("SJNL")
                    elif chamber == "lower":
                        journal_format = journal_template.format("HJNL")
                    else:
                        raise ValueError(f"Unknown chamber: {chamber}")

                    date = datetime.strptime(filename, journal_format)
                    date = datetime.combine(
                        date, time(tzinfo=timezone(timedelta(hours=-5)))
                    )
                    yield self.scrape_journal(url, chamber, session, date)
                except ValueError:
                    journal_format = "%m-%d-%Y.pdf"
                    try:
                        date = datetime.strptime(filename, journal_format)
                    except ValueError:
                        msg = "{} doesn't smell like a date. Skipping."
                        self.logger.info(msg.format(filename))

    def scrape_journal(self, url, chamber, session, date):

        filename, response = self.urlretrieve(url)
        self.logger.info(f"Saved journal to {filename}")
        all_text = convert_pdf(filename, type="text")

        lines = all_text.split(b"\n")
        lines = [line.decode("utf-8") for line in lines]
        lines = [
            line.strip()
            .replace("–", "-")
            .replace("―", '"')
            .replace("‖", '"')
            .replace("“", '"')
            .replace("”", '"')
            for line in lines
        ]

        # Do not process headers or completely empty lines
        header_date_re = re.compile(r"\d+\w{2} Day\s+\w+DAY, \w+ \d{1,2}, \d{4}\s+\d+")
        header_journal_re = re.compile(r"\d+\s+JOURNAL OF THE \w+\s+\d+\w{2} Day")
        lines = iter(
            [
                line
                for line in lines
                if not (
                    line == ""
                    or header_date_re.match(line)
                    or header_journal_re.match(line)
                )
            ]
        )

        # bill_id -> motion -> count
        motions_per_bill = collections.defaultdict(collections.Counter)

        bill_re = re.compile(r"\(\s*([A-Z\.]+\s\d+)\s*\)")
        chamber_motion_re = {
            "upper": re.compile(r".* the vote was:\s*"),
            "lower": re.compile(r'.*Shall.*(?:\?"?|")(\s{bill_re.pattern})?\s*'),
        }

        for line in lines:
            # Go through with vote parse if any of
            # these conditions match.
            if not line.startswith("On the question") or "shall" not in line.lower():
                continue

            # Get the bill_id
            bill_id = None

            while not chamber_motion_re[chamber].match(line, re.IGNORECASE):
                line += " " + next(lines)

            try:
                bill_id = bill_re.search(line).group(1)
            except AttributeError:
                self.warning(f"This motion did not pertain to legislation: {line}")
                continue

            # Get the motion text
            motion_re = r"""
                    ^On\sthe\squestion\s  # Precedes any motion
                    "+  # Motion is preceded by a quote mark (or two)
                    (Shall\s.+?\??)  # The motion text begins with "Shall"
                    \s*(?:\?"?|"|’)\s+  # Motion is followed by a question mark and/or a quote mark
                    (?:{})?  # If the vote regards a bill, its number is listed
                    {}  # Senate has trailing text
                    \s*$
                    """.format(
                # in at least one case [SF 457 from 2020] the bill number is followed by )0
                # seemingly just a typo, this gets around that
                bill_re.pattern,
                r",?.*?the\svote\swas:" if chamber == "upper" else r"\d?",
            )
            # print("motion candidate line:", line)
            motion = re.search(motion_re, line, re.VERBOSE | re.IGNORECASE)
            if motion:
                motion = motion.group(1)

            for word, letter in (("Senate", "S"), ("House", "H"), ("File", "F")):

                if bill_id is None:
                    return

                bill_id = bill_id.replace(word, letter)

            bill_id = bill_id.replace(".", "")

            bill_chamber = dict(h="lower", s="upper")[bill_id.lower()[0]]
            votes, passed = self.parse_votes(lines)

            # at the very least, there should be a majority
            # for the bill to have passed, so check that,
            # but if the bill didn't pass, it could still be OK if it got a majority
            # eg constitutional amendments
            if not (
                (passed == (votes["yes_count"] > votes["no_count"])) or (not passed)
            ):
                self.error("The bill passed without a majority?")
                raise ValueError("invalid vote")

            # also throw a warning if the bill failed but got a majority
            # it could be OK, but is probably something we'd want to check
            if not passed and votes["yes_count"] > votes["no_count"]:
                self.logger.warning(
                    f"{bill_id} got a majority but did not pass. "
                    "Could be worth confirming."
                )
            # ternary operator to define `result` cleanly
            result = "pass" if passed else "fail"

            # check for duplicate motions and number second and up if needed
            motion_text = re.sub(r"\xad", "-", motion)
            motions_per_bill[bill_id][motion_text] += 1
            new_count = motions_per_bill[bill_id][motion_text]
            if new_count > 1:
                motion_text += f" #{new_count}"

            vote = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=motion_text,
                result=result,
                classification="passage",
                legislative_session=session,
                bill=bill_id,
                bill_chamber=bill_chamber,
            )

            # add votes and counts
            for vtype in ("yes", "no", "absent", "abstain"):
                vcount = votes[f"{vtype}_count"] or 0
                vote.set_count(vtype, vcount)
                for voter in votes[f"{vtype}_votes"]:
                    vote.vote(vtype, voter)

            vote.add_source(url)
            yield vote

    def parse_votes(self, lines):
        counts = collections.defaultdict(list)
        DONE = 1
        boundaries = [
            # Senate journal.
            ("Yeas", "yes"),
            ("Nays", "no"),
            ("Absent", "absent"),
            ("Present", "abstain"),
            ("Amendment", DONE),
            ("Resolution", DONE),
            ("The senate joint resolution", DONE),
            ("Bill", DONE),
            # House journal.
            ("The ayes were", "yes"),
            ("The yeas were", "yes"),
            ("The nays were", "no"),
            ("Absent or not voting", "absent"),
            ("The bill", DONE),
            ("The committee", DONE),
            ("The resolution", DONE),
            ("The motion", DONE),
            ("Division", DONE),
            ("The joint resolution", DONE),
            ("Under the", DONE),
        ]
        passage_strings = ["passed", "adopted", "prevailed"]

        def is_boundary(text, patterns={}):
            for blurb, key in boundaries:
                if text.strip().startswith(blurb):
                    return key

        vote_re = re.compile(r"\d+")
        """
        First step:
        move to the first line that has a "boundary" string
        """
        while True:
            text = next(lines)
            if is_boundary(text):
                break

        """
        Second step:
        Start actually parsing lines for votes until we find a "DONE" marker
        This step can be confusing because of the inner while loop that _also_
        iterates the `lines` object forward
        Because of this pattern, we need to handle the edge case of a vote object
        not having a clear is_boundary() demarcation before the end of the current journal.
        We currently handle this by catching StopIteration errors in both the inner
        _and_ outer loops.
        """
        while True:
            key = is_boundary(text)
            if key is DONE:
                try:
                    passage_line = text + " " + next(lines)
                except StopIteration:
                    """
                    we just don't add any additional lines here
                    no need for a log message. If it still matches
                    a passage_string, cool
                    """
                    passage_line = text
                passed = False
                if any(p in passage_line for p in passage_strings):
                    passed = True
                break

            # Get the vote count.
            m = vote_re.search(text)
            if not m:
                if "none" in text:
                    votecount = 0
            else:
                votecount = int(m.group())
            counts[f"{key}_count"] = votecount

            # Get the voter names.
            while True:
                try:
                    text = next(lines)
                except StopIteration:
                    self.logger.warning("End of file while still iterating on voters")
                    # hack to force break of outer loop
                    text = "Division"
                    break
                if is_boundary(text):
                    break
                elif not text.strip() or text.strip().isdigit():
                    continue
                else:
                    counts[f"{key}_votes"].extend(
                        [name.strip() for name in self.split_names(text)]
                    )

        return counts, passed

    def split_names(self, text):
        junk = ["Presiding", "Mr. Speaker", "Spkr.", "."]
        text = text.strip()
        chunks = text.split()[::-1]
        name = [chunks.pop()]
        names = []
        while chunks:
            chunk = chunks.pop()
            if len(chunk) < 3:
                name.append(chunk)
            elif name[-1] in ("Mr.", "Van", "De", "Vander"):
                name.append(chunk)
            else:
                name = " ".join(name).strip(",")
                if name and (name not in names) and (name not in junk):
                    names.append(name)

                # Seed the next loop.
                name = [chunk]

        # Similar changes to the final name in the sequence.
        name = " ".join(name).strip(",")
        if names and len(name) < 3:
            names[-1] += f" {name}"
        elif name and (name not in names) and (name not in junk):
            names.append(name)
        return names
