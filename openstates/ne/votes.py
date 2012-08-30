import os
import re
import datetime

from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

BILL_RE = re.compile('^LEGISLATIVE (BILL|RESOLUTION) (\d+A?).')
DATE_RE = re.compile('(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) (\d+), (\d{4})')
QUESTION_RE = re.compile("(?:the question is, '|The question shall be, ')(.+)")
QUESTION_MATCH_END = "' \""
YES_RE = re.compile('Voting in the affirmative, (\d+)')
NO_RE = re.compile('Voting in the negative, (\d+)')
PRESENT_RE = re.compile('Present and not voting, (\d+)')
EXCUSED_RE = re.compile('Excused and not voting, (\d+)')


class NEVoteScraper(VoteScraper):
    state = 'ne'

    def scrape(self, session, chambers):
        urls = {'102': ['http://www.nebraskalegislature.gov/FloorDocs/Current/PDF/Journal/r1journal.pdf',
                        'http://www.nebraskalegislature.gov/FloorDocs/Current/PDF/Journal/r2journal.pdf'],
                '102S1': ['http://www.nebraskalegislature.gov/FloorDocs/Current/PDF/Journal/s1journal.pdf']}
        for url in urls[session]:
            self.scrape_journal(session, url)

    def scrape_journal(self, session, url):
        journal, resp = self.urlretrieve(url)
        text = convert_pdf(journal, type='text')
        lines = text.splitlines()

        #  state machine:
        #      None - undefined state
        #      question_quote - in question, looking for end quote
        #      pre-yes - vote is active, haven't hit yes votes yet
        #      yes     - yes votes
        #      no      - no votes
        #      other   - other votes
        state = None
        vote = None

        for line in lines:

            # skip headers
            if 'LEGISLATIVE JOURNAL' in line:
                continue

            # keep adding lines to question while quotes are open
            elif state == 'question_quote':
                question += ' %s' % line

            elif state in ('pre-yes', 'yes', 'no', 'other'):
                yes_match = YES_RE.match(line)
                no_match = NO_RE.match(line)
                present_match = PRESENT_RE.match(line)
                excused_match = EXCUSED_RE.match(line)
                if yes_match:
                    vote['yes_count'] = int(yes_match.group(1))
                    state = 'yes'
                elif no_match:
                    vote['no_count'] = int(no_match.group(1))
                    state = 'no'
                elif present_match:
                    vote['other_count'] += int(present_match.group(1))
                    state = 'other'
                elif excused_match:
                    vote['other_count'] += int(excused_match.group(1))
                    state = 'other'
                elif line:
                    people = re.split('\s{3,}', line)
                    try:
                        func = {'yes': vote.yes, 'no': vote.no,
                                'other': vote.other}[state]
                    except KeyError:
                        self.warning('line showed up in pre-yes state: %s',
                                     line)
                    for p in people:
                        if p:
                            func(p)

            # check the text against our regexes
            bill_match = BILL_RE.match(line)
            question_match = QUESTION_RE.findall(line)
            date_match = DATE_RE.findall(line)
            if bill_match:
                bill_type, bill_id = bill_match.groups()
                if bill_type == 'BILL':
                    bill_id = 'LB ' + bill_id
                elif bill_type == 'RESOLUTION':
                    bill_id = 'LR ' + bill_id
            elif question_match:
                question = question_match[0]
                state = 'question_quote'
            elif date_match:
                date = datetime.datetime.strptime(' '.join(date_match[0]),
                                                  '%B %d %Y')

            # line just finished a question
            if state == 'question_quote' and QUESTION_MATCH_END in question:
                question = re.sub('\s+', ' ',
                              question.replace(QUESTION_MATCH_END, '').strip())
                # save prior vote
                if vote:
                    self.save_vote(vote)
                vote = Vote(bill_id=bill_id, session=session,
                            bill_chamber='upper', chamber='upper',
                            motion=question, type='passage', passed=False,
                            date=date, yes_count=0, no_count=0, other_count=0)
                vote.add_source(url)
                state = 'pre-yes'

        # save final vote
        if vote:
            self.save_vote(vote)
