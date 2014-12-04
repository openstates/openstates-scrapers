import requests.exceptions
from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf
import datetime
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
        chamber_name = 'house' if chamber == 'lower' else 'senate'
        session_slug = {'62': '62-2011', '63': '63-2013', '64': '64-2015'}[session]

        # Open the web page that contains all of the session's PDFs, and open each
        url = "http://www.legis.nd.gov/assembly/%s/journals/%s-journal.html" % (
            session_slug, chamber_name)
        page = self.lxmlize(url)
        pdfs = page.xpath("//a[contains(@href, '.pdf')]")
        for pdf in pdfs:

            # Initialize information about the vote parsing
            results = {}
            cur_date = None
            in_motion = False
            cur_vote = None
            in_vote = False
            cur_motion = ""

            # Determine which URLs the information was pulled from
            pdf_url = pdf.attrib['href']

            try:
                (path, response) = self.urlretrieve(pdf_url)
            except requests.exceptions.ConnectionError:
                continue

            # Convert the PDF to text, and check each line of that text
            data = convert_pdf(path, type='text')
            os.unlink(path)
            lines = data.splitlines()
            for line in lines:

                # Determine the date of the document
                date = re.findall(date_re, line)
                if date != [] and not cur_date:
                    date = date[0][0]
                    cur_date = datetime.datetime.strptime(date, "%A, %B %d, %Y")

                # If the line contains a motion name, capture it
                if "question being" in line:
                    in_motion = True
                    cur_motion = line.strip()
                elif in_motion:
                    cur_motion += line.strip()

                # If a vote is indicated, prepare to capture it
                elif line.strip() == 'ROLL CALL':
                    in_vote = True

                # If votes are being processed, record the voting members
                elif in_vote and ":" in line:
                    cur_vote, who = line.split(":", 1)
                    who = [x.strip() for x in who.split(';')]
                    results[cur_vote] = who
                elif in_vote and cur_vote is not None:
                    who = [x.strip() for x in line.split(";")]
                    # print cur_vote
                    results[cur_vote].extend(who)

                # Empty lines should be skipped
                elif line.strip() == "":
                    in_motion = False

                # Likewise, VOTES FOR indicates the end of a motion and vote
                elif 'VOTES FOR' in line:
                    in_motion = False
                    in_vote = False

                # If the line regards the conclusion of a vote, process it specially
                elif True in [x in line.lower() for x in
                        ['passed', 'adopted', 'lost', 'failed']] and in_vote:
                    in_vote = False

                    # Pull the bill's name from the passage status
                    # If there appears to be no bill in processing, then disregard this
                    bills = re.findall(r"(?i)(H|S|J)(B|R|M) (\d+)", line)
                    if bills == [] or cur_motion.strip() == "":
                        results = {}
                        in_motion = False
                        cur_vote = None
                        continue

                    print "CM: ", cur_motion

                    cur_bill_id = "%s%s %s" % (bills[-1])

                    # Use the collected results to determine who voted which way
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

                    # Count the number of members voting each way
                    yes, no, other = len(res['yes']), len(res['no']), \
                                        len(res['other'])
                    chambers = {
                        "H": "lower",
                        "S": "upper",
                        "J": "joint"
                    }

                    # Identify the source chamber for the bill
                    try:
                        bc = chambers[cur_bill_id[0]]
                    except KeyError:
                        bc = 'other'

                    # If no date is found, do not process the vote
                    if cur_date is None:
                        self.warning("Cur-date is None. Passing.")
                        continue

                    # Create a Vote object based on the information collected
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

                    # For each category of voting members, add the individuals to the Vote object
                    for key in res:
                        obj = getattr(vote, key)
                        for person in res[key]:
                            obj(person)

                    self.save_vote(vote)

                    # With the vote successfully processed, wipe its data and continue to the next one
                    results = {}
                    in_motion = False
                    cur_vote = None
                    cur_motion = ""

                    # print bills
                    # print "VOTE TAKEN"
