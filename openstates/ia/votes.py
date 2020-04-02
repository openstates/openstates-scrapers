# -*- coding: utf8 -*-
from datetime import datetime, time, timezone, timedelta
import re
import collections
import lxml.etree

from openstates_core.utils import convert_pdf
from openstates_core.scrape import Scraper, VoteEvent


SITE_IDS = {
    "2019-2020": "88",
    "2017-2018": "87",
    "2015-2016": "86",
    "2013-2014": "85",
    "2011-2012": "84",
}


class IAVoteScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()

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
                        raise ValueError("Unknown chamber: {}".format(chamber))

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
        self.logger.info("Saved journal to %r" % filename)
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
        header_date_re = r"\d+\w{2} Day\s+\w+DAY, \w+ \d{1,2}, \d{4}\s+\d+"
        header_journal_re = r"\d+\s+JOURNAL OF THE \w+\s+\d+\w{2} Day"
        lines = iter(
            [
                line
                for line in lines
                if not (
                    line == ""
                    or re.match(header_date_re, line)
                    or re.match(header_journal_re, line)
                )
            ]
        )

        for line in lines:
            # Go through with vote parse if any of
            # these conditions match.
            if not line.startswith("On the question") or "shall" not in line.lower():
                continue

            # Get the bill_id
            bill_id = None
            bill_re = r"\(\s*([A-Z\.]+\s\d+)\s*\)"

            # The Senate ends its motion text with a vote announcement
            if chamber == "upper":
                end_of_motion_re = r".* the vote was:\s*"
            # The House may or may not end motion text with a bill name
            elif chamber == "lower":
                end_of_motion_re = r'.*Shall.*(?:\?"?|")(\s{})?\s*'.format(bill_re)

            while not re.match(end_of_motion_re, line, re.IGNORECASE):
                line += " " + next(lines)

            try:
                bill_id = re.search(bill_re, line).group(1)
            except AttributeError:
                self.warning(
                    "This motion did not pertain to legislation: {}".format(line)
                )
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
                bill_re, r",?.*?the\svote\swas:" if chamber == "upper" else ""
            )
            print(line)
            motion = re.search(motion_re, line, re.VERBOSE | re.IGNORECASE).group(1)

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
                    "The bill got a majority but did not pass. "
                    "Could be worth confirming."
                )

            result = ""
            if passed:
                result = "pass"
            else:
                result = "fail"

            vote = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=re.sub("\xad", "-", motion),
                result=result,
                classification="passage",
                legislative_session=session,
                bill=bill_id,
                bill_chamber=bill_chamber,
            )

            # add votes and counts
            for vtype in ("yes", "no", "absent", "abstain"):
                vcount = votes["{}_count".format(vtype)] or 0
                vote.set_count(vtype, vcount)
                for voter in votes["{}_votes".format(vtype)]:
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

        while True:
            text = next(lines)
            if is_boundary(text):
                break

        while True:
            key = is_boundary(text)
            if key is DONE:
                passage_line = text + " " + next(lines)
                passed = False
                if any(p in passage_line for p in passage_strings):
                    passed = True
                break

            # Get the vote count.
            m = re.search(r"\d+", text)
            if not m:
                if "none" in text:
                    votecount = 0
            else:
                votecount = int(m.group())
            counts["%s_count" % key] = votecount

            # Get the voter names.
            while True:
                text = next(lines)
                if is_boundary(text):
                    break
                elif not text.strip() or text.strip().isdigit():
                    continue
                else:
                    for name in self.split_names(text):
                        counts["%s_votes" % key].append(name.strip())

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
            names[-1] += " %s" % name
        elif name and (name not in names) and (name not in junk):
            names.append(name)
        return names
