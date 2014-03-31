import requests.exceptions
from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf
import datetime
import subprocess
import lxml
import os
import re

fin_re = r"(?i).*(?P<bill_id>(S|H|J)(B|R|M) \d+).*(?P<passfail>(passed|lost)).*"
date_re = r".*(?P<date>(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY), .*\d{1,2},\s\d{4}).*"

class NDVoteScraper(VoteScraper):
    jurisdiction = 'nd'

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page


    def scrape(self, chamber, session):
        chamber_name = 'senate' if chamber == 'lower' else 'house'
        session_slug = {'62': '62-2011', '63': '63-2013'}[session]

        url = "http://www.legis.nd.gov/assembly/%s/journals/%s-journal.html" % (
            session_slug, chamber_name)
        page = self.lxmlize(url)
        pdfs = page.xpath("//a[contains(@href, '.pdf')]")
        for pdf in pdfs:

            bill_id = None
            results = {}
            in_vote = False
            cur_date = None
            in_motion = False
            cur_vote = None
            in_vote = False
            cur_motion = ""

            pdf_url = pdf.attrib['href']

            try:
                (path, response) = self.urlretrieve(pdf_url)
            except requests.exceptions.ConnectionError:
                continue

            data = convert_pdf(path, type='text')
            os.unlink(path)
            lines = data.splitlines()
            for line in lines:
                date = re.findall(date_re, line)
                if date != [] and not cur_date:
                    date = date[0][0]
                    cur_date = datetime.datetime.strptime(date, "%A, %B %d, %Y")

                if line.strip() == "":
                    in_motion = False
                    continue

                if True in [x in line.lower() for x in ['passed', 'lost']] and in_vote:
                    in_vote = False
                    bills = re.findall(r"(?i)(H|S|J)(B|R|M) (\d+)", line)
                    if bills == [] or cur_motion.strip() == "":
                        bill_id = None
                        results = {}
                        in_vote = False
                        in_motion = False
                        cur_vote = None
                        in_vote = False
                        continue

                    print "CM: ", cur_motion

                    cur_bill_id = "%s%s %s" % (bills[-1])
                    keys = {
                        "YEAS": "yes",
                        "NAYS": "no",
                        "ABSENT AND NOT VOTING": "other"
                    }
                    res = {}
                    for key in keys:
                        if key in results:
                            res[keys[key]] = filter(lambda a: a != "",
                                                    results[key])
                        else:
                            res[keys[key]] = []

                    # results
                    results = {}
                    yes, no, other = len(res['yes']), len(res['no']), \
                                        len(res['other'])
                    chambers = {
                        "H": "lower",
                        "S": "upper",
                        "J": "joint"
                    }
                    try:
                        bc = chambers[cur_bill_id[0]]
                    except KeyError:
                        bc = 'other'

                    if cur_date is None:
                        self.warning("Cur-date is None. Passing.")
                        continue

                    vote = Vote(chamber,
                                cur_date,
                                cur_motion,
                                (yes > no),
                                yes,
                                no,
                                other,
                                session=session,
                                bill_id=cur_bill_id,
                                bill_chamber=bc)

                    vote.add_source(pdf_url)
                    vote.add_source(url)

                    for key in res:
                        obj = getattr(vote, key)
                        for person in res[key]:
                            obj(person)

                    self.save_vote(vote)


                    bill_id = None
                    results = {}
                    in_vote = False
                    in_motion = False
                    cur_vote = None
                    in_vote = False
                    cur_motion = ""

                    # print bills
                    # print "VOTE TAKEN"

                if 'VOTES FOR' in line:
                    in_motion = False
                    in_vote = False
                    continue

                if 'ABSET' in line:
                    if in_motion:
                        in_vote = True
                    in_motion = False

                if ":" in line and in_vote:
                    cur_vote, who = line.split(":", 1)
                    who = [x.strip() for x in who.split(';')]
                    results[cur_vote] = who
                    continue

                if in_vote:
                    if cur_vote is None:
                        continue

                    who = [x.strip() for x in line.split(";")]
                    for person in who:
                        # print cur_vote
                        results[cur_vote].append(person)
                    continue

                if "question being" in line:
                    cur_motion = line.strip()
                    in_motion = True
                    continue

                if in_motion:
                    cur_motion += line.strip()
                    continue

                if line.strip() == 'ROLL CALL':
                    in_vote = True
