import re
import datetime
import logging
from collections import Counter

from pupa.scrape import VoteEvent, Scraper
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone, SESSION_KEYS

logger = logging.getLogger('openstates')


class ORVoteScraper(Scraper):
    tz = get_timezone()
    chamber_code = {'S': 'upper', 'H': 'lower', 'J': 'legislature'}
    vote_code = {
            'Aye': 'yes',
            'Nay': 'no',
            'Excused': 'absent',
            'Excused for Business': 'absent',
            'Absent': 'absent',
            }

    vote_classifiers = (
        ('.*Introduction and first reading.*',
         ['introduction', 'reading-1']),

        ('.*First reading.*', ['introduction', 'reading-1']),
        ('.*Second reading.*', ['reading-2']),
        ('.*Referred to .*', ['referral-committee']),
        ('.*Assigned to Subcommittee.*', ['referral-committee']),
        ('.*Recommendation: Do pass.*', ['committee-passage-favorable']),
        ('.*Governor signed.*', ['executive-signature']),
        ('.*Third reading.* Passed', ['passage', 'reading-3']),
        ('.*Third reading.* Failed', ['failure', 'reading-3']),
        ('.*President signed.*', ['passage']),
        ('.*Speaker signed.*', ['passage']),
        ('.*Final reading.* Adopted', ['passage']),
        ('.*Read third time .* Passed', ['passage', 'reading-3']),
        (r'.*Read\. .* Adopted.*', ['passage']),
    )

    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            session = self.latest_session()

        yield from self.scrape_votes(session)

    def scrape_votes(self, session):
        self.session_key = SESSION_KEYS[session]
        self.legislators = index_legislators(self, self.session_key)
        measures_response = self.api_client.get('votes', page=500, session=self.session_key)

        for measure in measures_response:
            bid = '{} {}'.format(measure['MeasurePrefix'], measure['MeasureNumber'])

            measure_history = measure['MeasureHistoryActions']
            for event in measure_history:
                if event['MeasureVotes']:
                    tally = self.tally_votes(event, 'measure')
                    passed = self.passed_vote(tally)

                    classification = self.determine_vote_classifiers(event['ActionText'])
                    when = datetime.datetime.strptime(event['ActionDate'], '%Y-%m-%dT%H:%M:%S')
                    when = self.tz.localize(when)

                    vote = VoteEvent(
                        start_date=when,
                        bill_chamber=self.chamber_code[bid[0]],
                        motion_text=event['ActionText'],
                        classification=classification,
                        result='pass' if passed else 'fail',
                        legislative_session=session,
                        bill=bid,
                        chamber=self.chamber_code[event['Chamber']]
                    )

                    vote.set_count('yes', tally['yes'])
                    vote.set_count('no', tally['no'])
                    vote.set_count('absent', tally['absent'])

                    vote_call = event['MeasureVotes']
                    self.add_individual_votes(vote, vote_call, 'measure')

                    vote.add_source(
                        'https://olis.leg.state.or.us/liz/{session}'
                        '/Measures/Overview/{bid}'.format(
                            session=self.session_key,
                            bid=bid.replace(' ', '')
                        ))

                    yield vote

            committee_history = measure['CommitteeAgendaItems']
            for event in committee_history:
                if event['CommitteeVotes']:
                    tally = self.tally_votes(event, 'committee')
                    passed = self.passed_vote(tally)

                    # there is at least one event w/o an Action listed
                    action = event['Action'] or event['Comments']

                    classification = self.determine_vote_classifiers(action)
                    when = datetime.datetime.strptime(event['MeetingDate'], '%Y-%m-%dT%H:%M:%S')
                    when = self.tz.localize(when)

                    vote = VoteEvent(
                        start_date=when,
                        bill_chamber=self.chamber_code[bid[0]],
                        motion_text=action,
                        classification=classification,
                        result='pass' if passed else 'fail',
                        legislative_session=session,
                        bill=bid,
                        chamber=self.chamber_code[event['CommitteCode'][0]]
                    )

                    vote.set_count('yes', tally['yes'])
                    vote.set_count('no', tally['no'])
                    vote.set_count('absent', tally['absent'])

                    vote_call = event['CommitteeVotes']
                    self.add_individual_votes(vote, vote_call, 'committee')

                    meeting_date = when.strftime('%Y-%m-%d-%H-%M')
                    vote.add_source(
                        'https://olis.leg.state.or.us/liz/{session}/Committees'
                        '/{committee}/{meeting_date}/{bid}/Details'.format(
                            session=self.session_key,
                            committee=event['CommitteCode'],
                            meeting_date=meeting_date,
                            bid=bid.replace(' ', '')
                        ))

                    yield vote

    def add_individual_votes(self, vote, vote_call, vote_type):
        if vote_type == 'measure':
            vote_meaning = 'Vote'
        elif vote_type == 'committee':
            vote_meaning = 'Meaning'

        for voter in vote_call:
            try:
                voter_name = self.legislators[voter['VoteName']]
            except KeyError:
                logger.warn('Legislator {} not found in session {}'.format(
                    voter['VoteName'], self.session_key))
                voter_name = voter['VoteName']
            if voter[vote_meaning] == 'Aye':
                vote.yes(voter_name)
            elif voter[vote_meaning] == 'Nay':
                vote.no(voter_name)
            else:
                vote.vote('absent', voter_name)

    @staticmethod
    def passed_vote(tally):
        return float(tally['yes']) / (tally['yes'] + tally['no']) > 0.5

    def tally_votes(self, event, vote_type):
        if vote_type == 'measure':
            tally = dict(Counter([self.vote_code[v['Vote']] for v in event['MeasureVotes']]))
        elif vote_type == 'committee':
            tally = dict(Counter([self.vote_code[v['Meaning']] for v in event['CommitteeVotes']]))
        for code in list(self.vote_code.values()):
            if code not in tally:
                tally[code] = 0
        return tally

    def determine_vote_classifiers(self, vote):
        types = []
        for expr, types_ in self.vote_classifiers:
            m = re.match(expr, vote)
            if m:
                types += types_
        return types
