'''
Mission
========

Accurately guess when a bill is currently in a particular committee.
Also, accurately guess which committee and bill has been in and how
long the bill spent in those committees.

The problem
===============

Many states provide actions when a bill is referred, but not when
it is reported.

Possible Solution
==================

On a state-by-state basis, create lists of actions that necessarily
or at least probably indicate that previously referred bill is probably
out of the committee it was referred to. To elaborate, when a bill passes
the introduced chamber, it's a good bet that it has been reported following
its initial committee referral.
'''
import itertools
from collections import defaultdict
import logbook

from billy.models import db


logger = logbook.Logger('elf-owl')


class RecursiveDotDict(dict):
    def __getattr__(self, name):
        attr = self[name]
        if isinstance(attr, dict):
            attr = RecursiveDotDict(attr)
        return attr


class Action(RecursiveDotDict):

    @property
    def types(self):
        return set(self.type)

    @property
    def id(self):
        bill = self.bill
        return bill['_id'], bill['actions'].index(self), self['actor']


class Referral(dict):

    def __init__(self, referring_action=None, reporting_action=None):
        self['referring_action'] = referring_action
        self['reporting_action'] = reporting_action
        self['status'] = 'pending'

    def set_reporting_action(self, action):
        self['reporting_action'] = action
        self['status'] = 'complete'


class BaseDetectorThingy(object):

    referred_types = set(['committee:referred'])
    reported_types = set([
        'committee:passed',
        'committee:passed:favorable',
        'committee:passed:unfavorable',
        ])
    reported_inferred_types = set([
        'reading:2:passed'
        'bill:passed',
        ])

    def __init__(self, bill):
        action_cls = type('Action', (Action,), dict(bill=bill))
        self.referrals = defaultdict(list)
        self.bill = bill
        actions = map(action_cls, bill['actions'])

        self.actions = actions

    def pending_referrals(self):
        '''All the referrals that haven't (ostensibly) concluded
        yet. Yield them in reverse order though.
        '''
        referrals = sorted(
            itertools.chain.from_iterable(self.referrals.values()),
            key=lambda ref: ref['referring_action']['date'],
            reverse=True)
        for referral in referrals:
            if not referral['reporting_action']:
                yield referral

    def check(self):
        for k, v in self.referrals.items():
            done = []
            v = list(v)
            while v:
                x = v.pop()
                if x in done:
                    import pdb;pdb.set_trace()
                done.append(x)


    def get_referrals(self):
        referred_types = self.referred_types
        reported_types = self.reported_types
        reported_inferred_types = self.reported_inferred_types
        bogus_referrals = []
        for action in self.actions:
            # self.check()

            if action.types & (reported_types | reported_inferred_types):
                logger.debug('REPORTED %r %r' % (action['date'], action['action']))

                # Close the most recent one.
                if self.referrals:
                    pending = self.pending_referrals()
                    recent = next(pending)

                    recent['reporting_action'] = action

                    # The rest are marked complete without
                    # a reporting action, per the assumption
                    # that a bill can only be referred to one
                    # committe at a time.
                    for referral in pending:
                        referral['status'] = 'complete'

                else:
                    logger.warning('No referral: %r' % action['action'])

            if action.types & referred_types:
                logger.debug('REFERRED %r, %r' % (action['date'], action['action']))

                # Is the committee unambigiuously identified in this action?
                committee_ids = [obj['id'] for obj in action.related_entities
                                 if obj['type'] == 'committee']
                committee_ids = filter(None, committee_ids)

                # Make sure there's only one tagged committee
                # in the referring action.
                try:
                    assert len(committee_ids) == 1
                except AssertionError:
                    if len(committee_ids) == 0:
                        msg = "No committees captured in action: %r"
                    elif len(committee_ids) > 1:
                        msg = "Ambiguous referring committee: %r"
                    logger.warning(msg % action.action)
                    bogus_referrals.append(Referral(action))
                    continue

                # A list of all referrals of this bill to this committee.
                key = committee_ids.pop(), action['actor']
                committee_referrals = self.referrals[key]
                committee_referrals.append(Referral(action))

        for key, value in self.referrals.items():
            import pprint
            pprint.pprint(value)
            # import pdb;pdb.set_trace()


def main(abbr, *args):

    bills = db.bills.find({
        'state': abbr,
        'actions.type': 'committee:refereed',
        'actions.type': 'committee:passed'
        })

    for bb in bills:
        print '\n\n-------', bb['bill_id'], '------\n\n'
        dt = BaseDetectorThingy(bb)
        dt.get_referrals()

        tags = ['committee:referred', 'committee:passed'
                'committee:passed:favorable',
                'committee:passed:unfavorable',]
        acs = filter(lambda a: set(tags) & set(a['type']), bb['actions'])
        for ac in acs:
            print 'text: %(action)s, tags: %(type)r' % ac
        import pdb;pdb.set_trace()


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])