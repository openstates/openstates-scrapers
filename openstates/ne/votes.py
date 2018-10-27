import re
import datetime

from pupa.scrape import Scraper, VoteEvent
from pupa.utils.generic import convert_pdf

BILL_RE = re.compile(r'^LEGISLATIVE (BILL|RESOLUTION) (\d+C?A?).')
VETO_BILL_RE = re.compile(r'- Override (?:Line-Item )?Veto on (\w+)')
DATE_RE = re.compile(
    r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) '
    r'(\d+), (\d{4})'
)
QUESTION_RE = re.compile("(?:the question is, '|The question shall be, ')(.+)")
QUESTION_MATCH_END = r"' \""
YES_RE = re.compile(r'Voting in the affirmative, (\d+)')
NO_RE = re.compile(r'Voting in the negative, (\d+)')
NOT_VOTING_RE = re.compile(r'(?:Present|Absent|Excused)?(?: and )?[Nn]ot voting, (\d+)')


class NEVoteScraper(Scraper):
    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        urls = {
            '105': [
                'http://www.nebraskalegislature.gov/FloorDocs/Current/PDF/Journal/r1journal.pdf',
            ],
        }
        self._seen = set()
        for url in urls[session]:
            yield from self.scrape_journal(session, url)

    def scrape_journal(self, session, url):
        journal, resp = self.urlretrieve(url)
        text = convert_pdf(journal, type='text').decode()
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
        question = None
        date = None
        other_count = 0

        for line in lines:
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
                    vote.set_count('yes', int(yes_match.group(1)))
                    state = 'yes'
                elif no_match:
                    vote.set_count('no', int(no_match.group(1)))
                    state = 'no'
                elif other_match:
                    other_count += int(other_match.group(1))
                    state = 'other'
                elif 'having voted in the affirmative' in line:
                    vote.set_count('other', other_count)
                    vote.result = 'pass'
                    state = None
                    vote.validate()
                    yield vote
                    vote = None
                    other_count = 0
                elif 'Having failed' in line:
                    vote.set_count('other', other_count)
                    vote.result = 'fail'
                    state = None
                    vote.validate()
                    yield vote
                    vote = None
                    other_count = 0
                elif line:
                    people = re.split(r'\s{3,}', line)
                    # try:
                    # except KeyError:
                    #     self.warning('line showed up in pre-yes state: %s',
                    #                  line)
                    for p in people:
                        if p:
                            # special cases for long name w/ 1 space
                            if p.startswith(('Lautenbaugh ', 'Langemeier ', 'McCollister ',
                                             'Pansing Brooks ', 'Schumacher ')):
                                p1, p2 = p.split(' ', 1)
                                vote.vote(state, p1)
                                vote.vote(state, p2)
                            else:
                                vote.vote(state, p)

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
                question = re.sub(r'\s+', ' ',
                                  question.replace(QUESTION_MATCH_END, '').strip())

                if not bill_id:
                    raise Exception('cannot save vote without bill_id')

                # save prior vote
                vtuple = (bill_id, date, question)
                if vtuple in self._seen:
                    vote = None
                    continue
                else:
                    self._seen.add(vtuple)

                vote = VoteEvent(
                    bill=bill_id,
                    bill_chamber='legislature',
                    chamber='legislature',
                    legislative_session=session,
                    start_date=date.strftime('%Y-%m-%d'),
                    motion_text=question,
                    classification='passage',
                    result='fail',
                )
                vote.add_source(url)
                state = 'pre-yes'
                # reset bill_id and question
                bill_id = question = None
