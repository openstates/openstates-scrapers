import os
import re
import datetime

from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import convert_pdf

BILL_RE = re.compile('^LEGISLATIVE (BILL|RESOLUTION) (\d+C?A?).')
VETO_BILL_RE = re.compile('MOTION - Override (?:Line-Item )?Veto on (\w+)')
DATE_RE = re.compile('(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) (\d+), (\d{4})')
QUESTION_RE = re.compile("(?:the question is, '|The question shall be, ')(.+)")
QUESTION_MATCH_END = "' \""
YES_RE = re.compile('Voting in the affirmative, (\d+)')
NO_RE = re.compile('Voting in the negative, (\d+)')
NOT_VOTING_RE = re.compile('(?:Present|Absent|Excused)?(?: and )?[Nn]ot voting, (\d+)')


class NEVoteScraper(VoteScraper):
    jurisdiction = 'ne'

    def scrape(self, session, chambers):
        urls = {'104': ['http://www.nebraskalegislature.gov/FloorDocs/Current/PDF/Journal/r1journal.pdf',]}
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

        for line_num, line in enumerate(lines):
            date_match = DATE_RE.findall(line)

            # skip headers
            if 'LEGISLATIVE JOURNAL' in line:
                continue

            elif date_match:
                date = datetime.datetime.strptime(' '.join(date_match[0]),
                                                  '%B %d %Y')
                continue

            # keep adding lines to question while quotes are open
            elif state == 'question_quote':
                question += ' %s' % line

            elif state in ('pre-yes', 'yes', 'no', 'other'):
                yes_match = YES_RE.match(line)
                no_match = NO_RE.match(line)
                other_match = NOT_VOTING_RE.match(line)
                if yes_match:
                    vote['yes_count'] = int(yes_match.group(1))
                    state = 'yes'
                elif no_match:
                    vote['no_count'] = int(no_match.group(1))
                    state = 'no'
                elif other_match:
                    vote['other_count'] += int(other_match.group(1))
                    state = 'other'
                elif 'having voted in the affirmative' in line:
                    vote['passed'] = True
                    state = None
                    vote.validate()
                    self.save_vote(vote)
                    vote = None
                elif 'Having failed' in line:
                    vote['passed'] = False
                    state = None
                    vote.validate()
                    self.save_vote(vote)
                    vote = None
                elif line:
                    people = re.split('\s{3,}', line)
                    #try:
                    func = {'yes': vote.yes, 'no': vote.no,
                            'other': vote.other}[state]
                    #except KeyError:
                        #self.warning('line showed up in pre-yes state: %s',
                        #             line)
                    for p in people:
                        if p:
                            # special cases for long name w/ 1 space
                            if p.startswith(('Lautenbaugh ', 'Langemeier ', 'McCollister ', 'Pansing Brooks ')):
                                p1, p2 = p.split(' ', 1)
                                func(p1)
                                func(p2)
                            else:
                                func(p)

            # check the text against our regexes
            bill_match = BILL_RE.match(line)
            veto_match = VETO_BILL_RE.findall(line)
            question_match = QUESTION_RE.findall(line)
            if bill_match:
                bill_type, bill_id = bill_match.groups()
                if bill_type == 'BILL':
                    bill_id = 'LB ' + bill_id
                elif bill_type == 'RESOLUTION':
                    bill_id = 'LR ' + bill_id
            elif question_match:
                question = question_match[0]
                state = 'question_quote'
            elif veto_match:
                bill_id = veto_match[0]

            # line just finished a question
            if state == 'question_quote' and QUESTION_MATCH_END in question:
                question = re.sub('\s+', ' ',
                              question.replace(QUESTION_MATCH_END, '').strip())
                # save prior vote
                vote = Vote(bill_id=bill_id, session=session,
                            bill_chamber='upper', chamber='upper',
                            motion=question, type='passage', passed=False,
                            date=date, yes_count=0, no_count=0, other_count=0)
                vote.add_source(url)
                state = 'pre-yes'
                # reset bill_id and question
                bill_id = question = None
