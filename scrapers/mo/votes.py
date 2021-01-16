import os
import re
import pytz
import collections
import datetime as dt

from utils import LXMLMixin

from openstates.utils import convert_pdf
from openstates.scrape import Scraper, VoteEvent

motion_re = r"(?i)On motion of .*, .*"
bill_re = r"(H|S)(C|J)?(R|M|B) (\d+)"
date_re = (
    r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)"
    r", (\w+) (\d+), (\d+)"
)

TIMEZONE = pytz.timezone("America/Chicago")


class MOVoteScraper(Scraper, LXMLMixin):
    def _clean_line(self, obj):
        patterns = {"\xe2\x80\x94": "-", "—": "-"}

        for pattern in patterns:
            obj = obj.replace(pattern, patterns[pattern])

        return obj

    def _get_pdf(self, url):
        (path, response) = self.urlretrieve(url)
        data = convert_pdf(path, type="text")
        os.remove(path)
        return data

    def _scrape_upper_chamber(self, session):
        if int(session[:4]) >= 2016:
            if len(session) == 4:
                # regular session
                url = "http://www.senate.mo.gov/%sinfo/jrnlist/default.aspx" % (
                    session[-2:],
                )
            else:
                # special session
                url = "http://www.senate.mo.gov/%sinfo/jrnlist/%sJournals.aspx" % (
                    session[-4:-2],
                    session[-2:],
                )
        else:
            url = "http://www.senate.mo.gov/%sinfo/jrnlist/journals.aspx" % (
                session[-2:]
            )

        vote_types = {
            "YEAS": "yes",
            "NAYS": "no",
            "Absent with leave": "other",
            "Absent": "other",
            "Vacancies": "other",
        }

        page = self.lxmlize(url)
        journs = page.xpath("//table")[0].xpath(".//a")
        for a in journs:
            pdf_url = a.attrib["href"]
            data = self._get_pdf(pdf_url).decode()
            lines = data.split("\n")

            in_vote = False
            cur_date = None
            vote_type = "other"
            cur_bill = ""
            cur_motion = ""
            bc = None
            vote = {}
            counts = collections.defaultdict(int)

            for line in lines:
                line = line.strip()

                if cur_date is None:
                    matches = re.findall(date_re, line)
                    if matches != []:
                        date = matches[0]
                        date = "%s, %s %s, %s" % date
                        date = dt.datetime.strptime(date, "%A, %B %d, %Y")
                        cur_date = date

                matches = re.findall(motion_re, line)
                if matches != []:
                    cont = False
                    for x in matches:
                        if "vote" in x.lower():
                            cur_motion = x
                            bill = re.findall(bill_re, x)
                            if bill != []:
                                bc = {"H": "lower", "S": "upper", "J": "legislature"}[
                                    bill[0][0]
                                ]

                                cur_bill = "%s%s%s %s" % bill[0]
                            in_vote = True
                            cont = True
                    if cont:
                        continue
                if in_vote:
                    if is_vote_end(line):
                        in_vote = False
                        yes, no, other = counts["yes"], counts["no"], counts["other"]
                        if bc is None:
                            continue

                        v = VoteEvent(
                            start_date=TIMEZONE.localize(date),
                            motion_text=cur_motion,
                            result="pass" if yes > no else "fail",
                            legislative_session=session,
                            classification="passage",
                            bill=cur_bill,
                            bill_chamber=bc,
                        )

                        v.add_source(url)
                        v.add_source(pdf_url)

                        v.set_count("yes", yes)
                        v.set_count("no", no)
                        v.set_count("other", other)

                        for key in vote:
                            for person in vote[key]:
                                v.vote(key, person)

                        yield v
                        vote = {}
                        counts = collections.defaultdict(int)
                        continue
                    if "Journal of the Senate" in line:
                        continue
                    if re.match(
                        r".*(Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday), .* \d+, \d+.*",
                        line,
                    ):
                        continue

                    found = False
                    rl = None
                    for vote_type in list(vote_types):
                        if line.lower().startswith(vote_type.lower()):
                            if "none" in line.lower():
                                continue

                            if "Senator" in line and "Senators" not in line:
                                line = self._clean_line(line)
                                line = line[len(vote_type) :]
                                line = line.replace("-Senator ", "")
                                rl = line
                            vote_category = vote_types[vote_type]
                            found = True
                            if vote_category not in vote:
                                vote[vote_category] = []
                    if found and rl is None:
                        continue
                    elif rl:
                        line = rl

                    names = [self._clean_line(x) for x in line.strip().split()]
                    if names == []:
                        continue

                    lname = names[-1]
                    lname = lname.rsplit("-", 1)
                    if len(lname) > 1:
                        person, count = lname
                        if count.isdigit() is False:
                            continue

                        names.pop(-1)
                        names.append(person)
                        counts[vote_category] += int(count)

                    for name in names:
                        vote[vote_category].append(name)

    def _scrape_lower_chamber(self, session):
        # house_url = 'http://www.house.mo.gov/journallist.aspx'
        yield from ()

    #  Ugh, so, the PDFs are in nasty shape. Scraping them is a mess, with
    #  crazy spacing to break up the names. Most votes aren't on bills, but rather
    #  the agenda of the day.

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        if chamber in ["upper", None]:
            yield from self._scrape_upper_chamber(session)
        if chamber in ["lower", None]:
            yield from self._scrape_lower_chamber(session)


def is_vote_end(line):
    return (
        (line == line.upper() and line.strip() != "")
        or "The President" in line
        or (
            "senator" in line.lower()
            and ("moved" in line.lower() or "requested" in line.lower())
        )
        or "assumed the chair" in line.lower()
    )
