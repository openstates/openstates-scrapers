from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

import datetime as dt
import lxml
import re


SENATE_URL = 'http://www.senate.mo.gov/12info/jrnlist/journals.aspx'
HOUSE_URL = 'http://www.house.mo.gov/journallist.aspx'

motion_re = r"(?i)On motion of .*, .*"
bill_re = r"(H|S)(C|J)?(R|M|B) (\d+)"
date_re = r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)" \
           ", (\w+) (\d+), (\d+)"

class MOVoteScraper(VoteScraper):
    state = 'mo'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def get_pdf(self, url):
        (path, response) = self.urlretrieve(url)
        data = convert_pdf(path, type='text')
        return data

    def scrape_senate(self, session):
        url = SENATE_URL
        classes = {
            "YEAS": 'yes',
            "NAYS": 'no',
            "Absent": 'other',
            "Abset with leave": 'other',
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
            bc = ''
            vote = {}

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
                       "The President" in line:
                        in_vote = False
                        # print vote
                        # print cur_motion
                        yes, no, other = len(vote['yes']), len(vote['no']), \
                                             len(vote['other'])

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
                        continue
                    if "Journal of the Senate" in line:
                        continue
                    if re.match(
                        r".*(Monday|Tuesday|Wednesday|Thursday|Friday|" \
                         "Saturday|Sunday), .* \d+, \d+.*",
                        line):
                        continue

                    found = False
                    for klass in classes:
                        if line.startswith(klass):
                            vote_type = classes[klass]
                            found = True
                            vote[vote_type] = []
                    if found:
                        continue

                    names = line.strip().split()
                    if names == []:
                        continue

                    for name in names:
                        vote[vote_type].append(name)
                # else:
                #     print line

    def scrape_house(self, session):
        url = HOUSE_URL
        page = self.lxmlize(url)
        journs = page.xpath(
            "//span[@id='ContentPlaceHolder1_lblJournalListing']//a")
        for a in journs:
            data = self.get_pdf(a.attrib['href'])
            print data

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate(session)
        elif chamber == 'lower':
            self.scrape_house(session)
