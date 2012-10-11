from billy.scrape.votes import VoteScraper, Vote
import datetime
import subprocess
import lxml
import os
import re

journals = "http://www.leg.state.co.us/CLICS/CLICS%s/csljournals.nsf/jouNav?Openform&%s"

vote_re = re.compile((r"\s*"
           "YES\s*(?P<yes_count>\d+)\s*"
           "NO\s*(?P<no_count>\d+)\s*"
           "EXCUSED\s*(?P<excused_count>\d+)\s*"
           "ABSENT\s*(?P<abs_count>\d+).*"))


class COVoteScraper(VoteScraper):
    state = 'co'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_house(self, session):
        url = journals % (session, 'House')
        page = self.lxmlize(url)
        hrefs = page.xpath("//font//a")

        for href in hrefs:
            (path, response) = self.urlretrieve(href.attrib['href'])
            txt = "%s.txt" % (path)

            try:
                subprocess.check_call([
                    "pdftotext", "-layout", path
                ])
            except subprocess.CalledProcessError:
                # XXX: log this error
                continue

            in_vote = False
            cur_vote = {}
            cur_vote_count = None
            in_question = False
            cur_question = None

            for line in open(txt, 'r').readlines():
                if re.match("(\s+)?\d+.*", line) is None:
                    continue
                try:
                    _, line = line.strip().split(" ", 1)
                    line = line.strip()
                except ValueError:
                    in_vote = False
                    in_question = False
                    continue

                if in_question:
                    cur_question += line
                    continue

                if ("The question being" in line) or \
                   ("On motion of" in line) or \
                   ("the following" in line) or \
                   ("moved that the" in line):
                    cur_question = line
                    in_question = True


                if in_vote:
                    if line == "":
                        in_vote = False
                        continue

                    votes = re.findall("(?P<name>\w+)\s+(?P<vote>Y|N|A|E|\*)",
                                       line)
                    for person, v in votes:
                        cur_vote[person] = v

                    if votes == []:
                        in_vote = False
                        # save vote
                        print cur_vote
                        print cur_question
                        cur_vote = {}
                        in_question = False
                        cur_question = None
                        in_vote = False

                summ = vote_re.findall(line)
                if summ == []:
                    continue
                summ = summ[0]
                yes, no, exc, ab = summ
                yes, no, exc, ab = \
                        int(yes), int(no), int(exc), int(ab)
                other = exc + ab
                cur_vote_count = (yes, no, other)
                in_vote = True
                continue

            os.unlink(path)
            os.unlink(txt)

    def scrape_senate(self, session):
        url = journals % (session, 'Senate')
        page = self.lxmlize(url)
        hrefs = page.xpath("//font//a")

        for href in hrefs:
            (path, response) = self.urlretrieve(href.attrib['href'])
            try:
                subprocess.check_call([
                    "pdftotext", "-layout", path
                ])
            except subprocess.CalledProcessError:
                # XXX: log this error
                continue

            txt = "%s.txt" % (path)

            cur_bill_id = None
            cur_vote_count = None
            in_vote = False
            cur_question = None
            in_question = False
            known_date = None
            cur_vote = {}

            for line in open(txt).readlines():

                if not known_date:
                    dt = re.findall(r"(?i).*(?P<dt>(monday|tuesday|wednesday|thursday|friday|saturday|sunday).*, \d{4}).*", line)
                    if dt != []:
                        dt, dow = dt[0]
                        known_date = datetime.datetime.strptime(dt,
                            "%A, %B %d, %Y")

                if in_question:
                    line = line.strip()
                    if re.match("\d+", line):
                        in_question = False
                        continue
                    try:
                        line, _ = line.rsplit(" ", 1)
                        cur_question += line
                    except ValueError:
                        in_question = False
                        continue

                    cur_question += line
                if not in_vote:
                    summ = vote_re.findall(line)
                    if summ != []:
                        cur_vote = {}
                        cur_vote_count = summ[0]
                        in_vote = True
                        continue

                    if ("The question being" in line) or \
                       ("On motion of" in line) or \
                       ("the following" in line) or \
                       ("moved that the" in line):
                        cur_question, _ = line.strip().rsplit(" ", 1)
                        in_question = True

                    if line.strip() == "":
                        continue
                    first = line[0]
                    if first != " ":
                        if " " not in line:
                            # wtf
                            continue

                        bill_id, kruft = line.split(" ", 1)
                        if len(bill_id) < 3:
                            continue
                        if bill_id[0] != "H" and bill_id[0] != "S":
                            continue
                        if bill_id[1] not in ['B', 'J', 'R', 'M']:
                            continue

                        cur_bill_id = bill_id
                else:
                    line = line.strip()
                    try:
                        line, lineno = line.rsplit(" ", 1)
                    except ValueError:
                        in_vote = False
                        if cur_question is None:
                            continue

                        if cur_bill_id is None:
                            continue

                        # print cur_vote
                        # print cur_question
                        # print cur_bill_id
                        # print cur_vote_count

                        yes, no, exc, ab = cur_vote_count
                        other = int(exc) + int(ab)
                        yes, no, other = int(yes), int(no), int(other)

                        bc = {'H': 'lower', 'S': 'upper'}[cur_bill_id[0]]

                        vote = Vote('upper',
                                    known_date,
                                    cur_question,
                                    (yes > no),
                                    yes,
                                    no,
                                    other,
                                    session=session,
                                    bill_id=cur_bill_id,
                                    bill_chamber=bc)
                        for person in cur_vote:
                            howvote = cur_vote[person]
                            howvote = howvote.upper()
                            if howvote == 'Y':
                                vote.yes(person)
                            elif howvote == 'N':
                                vote.no(person)
                            else:
                                vote.other(person)
                        vote.add_source(href.attrib['href'])
                        self.save_vote(vote)

                        cur_vote, cur_question, cur_vote_count = (
                            None, None, None)
                        continue

                    vals = line.split()
                    vals = dict(zip(vals[0::2], vals[1::2]))
                    cur_vote.update(vals)

            os.unlink(path)
            os.unlink(txt)

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate(session)
        if chamber == 'lower':
            self.scrape_house(session)
