from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

import lxml
import re


SENATE_URL = 'http://www.senate.mo.gov/12info/jrnlist/journals.aspx'
HOUSE_URL = 'http://www.house.mo.gov/journallist.aspx'

motion_re = r"(?i)On motion of .*, .*"


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

    def scrape_senate(self):
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
            data = self.get_pdf(a.attrib['href'])
            lines = data.split("\n")

            in_vote = False
            vote_type = 'other'

            for line in lines:
                line = line.strip()
                matches = re.findall(motion_re, line)
                if matches != []:
                    hasvotes = ["vote" in x.lower() for x in matches]
                    in_vote = True in hasvotes
                    continue
                if in_vote:

                    if "The President" in line:
                        in_vote = False
                        continue
                    if line == line.upper() and line.strip() != "":
                        in_vote = False
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
                    if found:
                        continue
                    print line

    def scrape_house(self):
        url = HOUSE_URL
        page = self.lxmlize(url)
        journs = page.xpath(
            "//span[@id='ContentPlaceHolder1_lblJournalListing']//a")
        for a in journs:
            data = self.get_pdf(a.attrib['href'])
            print data

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate()
        elif chamber == 'lower':
            self.scrape_house()
