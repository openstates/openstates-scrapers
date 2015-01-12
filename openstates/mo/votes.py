from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

from openstates.utils import LXMLMixin
import datetime as dt
import lxml
import re
import os


SENATE_URL = 'http://www.senate.mo.gov/%sinfo/jrnlist/journals.aspx'
HOUSE_URL = 'http://www.house.mo.gov/journallist.aspx'

motion_re = r"(?i)On motion of .*, .*"
bill_re = r"(H|S)(C|J)?(R|M|B) (\d+)"
date_re = r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)" \
           ", (\w+) (\d+), (\d+)"


def _clean_line(obj):
    patterns = {
        "\xe2\x80\x94": "-"
    }
    for pattern in patterns:
        obj = obj.replace(pattern, patterns[pattern])

    return obj


class MOVoteScraper(VoteScraper, LXMLMixin):
    jurisdiction = 'mo'

    def get_pdf(self, url):
        (path, response) = self.urlretrieve(url)
        data = convert_pdf(path, type='text')
        os.remove(path)
        return data

    def scrape_senate(self, session):
        url = SENATE_URL % (session[-2:])
        classes = [
            "YEAS",
            "NAYS",
            "Absent with leave",
            "Absent",
            "Vacancies"
        ]
        klasses = {
            "YEAS": 'yes',
            "NAYS": 'no',
            "Absent with leave": 'other',
            "Absent": 'other',
            "Vacancies": 'other'
        }
        page = self.lxmlize(url)
        journs = page.xpath("//table")[0].xpath(".//a")
        for a in journs:
            pdf_url = a.attrib['href']
            data = self.get_pdf(pdf_url)
            lines = data.split("\n")

            in_vote = False
            cur_date = None
            vote_type = 'other'
            cur_bill = ''
            cur_motion = ''
            bc = None
            vote = {}
            counts = {
                "yes": 0,
                "no": 0,
                "other": 0
            }

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
                                bc = {'H': 'lower',
                                      'S': 'upper',
                                      'J': 'joint'}[bill[0][0]]

                                cur_bill = "%s%s%s %s" % bill[0]
                            in_vote = True
                            cont = True
                    if cont:
                        continue
                if in_vote:
                    if (line == line.upper() and line.strip() != "") or \
                       "The President" in line or (
                           "senator" in line.lower() and
                           (
                               "moved" in line.lower() or
                               "requested" in line.lower()
                           )
                       ) or \
                       "assumed the chair" in line.lower():
                        in_vote = False
                        # print vote
                        # print cur_motion
                        yes, no, other = counts['yes'], counts['no'], \
                                            counts['other']
                        if bc is None:
                            continue

                        v = Vote('upper',
                                  date,
                                  cur_motion,
                                  (yes > no),
                                  yes,
                                  no,
                                  other,
                                  session=session,
                                  bill_id=cur_bill,
                                  bill_chamber=bc)
                        v.add_source(url)
                        v.add_source(pdf_url)
                        for key in vote:
                            for person in vote[key]:
                                getattr(v, key)(person)

                        self.save_vote(v)
                        vote = {}
                        counts = {  # XXX: Fix this. Dupe'd.
                            "yes": 0,
                            "no": 0,
                            "other": 0
                        }
                        continue
                    if "Journal of the Senate" in line:
                        continue
                    if re.match(
                        r".*(Monday|Tuesday|Wednesday|Thursday|Friday|" \
                         "Saturday|Sunday), .* \d+, \d+.*",
                        line):
                        continue

                    found = False
                    rl = None
                    for klass in classes:
                        if line.lower().startswith(klass.lower()):
                            if "none" in line.lower():
                                continue

                            if "Senator" in line and not "Senators" in line:
                                line = _clean_line(line)
                                line = line[len(klass):]
                                line = line.replace("-Senator ", "")
                                rl = line
                            vote_type = klasses[klass]
                            found = True
                            if vote_type not in vote:
                                vote[vote_type] = []
                    if found and rl is None:
                        continue
                    elif rl:
                        line = rl

                    # print line
                    names = [_clean_line(x) for x in line.strip().split()]
                    if names == []:
                        continue

                    # print names
                    lname = names[-1]
                    lname = lname.rsplit("-", 1)
                    if len(lname) > 1:
                        person, count = lname
                        if count.lower() == 'none':
                            continue

                        names.pop(-1)
                        names.append(person)
                        counts[vote_type] += int(count)
                        # print counts

                    for name in names:
                        vote[vote_type].append(name)
                # else:
                #     print line

    def scrape_house(self, session):
        pass
#  Ugh, so, the PDFs are in nasty shape. Scraping them is a mess, with
#  crazy spacing to break up the names. Most votes aren't on bills, but rather
#  the agenda of the day.

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate(session)
        elif chamber == 'lower':
            self.scrape_house(session)
