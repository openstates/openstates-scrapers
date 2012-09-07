import sys
import re
import pprint

from billy import db


def get_actions(abbr):
    for bill in db.bills.find({'state': abbr}, fields=['actions']):
        for ac in bill['actions']:
            yield ac['action']

sub_patterns = {
    'vote_breakdown': ('\(Ayes (?P<yes_votes>\d+)\. Noes (?P<no_votes>\d+)\.'
                       '( Page (?P<page>\d+.))?\)'),
    'chamber': u'(Ordered to )?(the )?(?P<chamber>\S+)',
    'month_day': '(?P<month>\S+) (?P<day>\S+?)',
    'committee': '(?P<committee>.+?)',
    'committees': '(?P<committees>.+?)',
    'recommendation': '(?P<recommendation>.+?)',
    'sl_chapter': '(?P<sessionlaw_chapter>\d+)',
    'sl_year': '(?P<sessionlaw_year>\d+)',
    'page': '\(Page (?P<journal_page>\d+?)\.\)',
    }

# Regexes matching action text.
patterns = [
    u'From printer. May be heard in committee {month_day}',
    u'Referred to Com\. on {committee}',
    u'Referred to Coms\. on {committees}',
    u'To Coms\. on {committees}',
    u'Read third time. Urgency clause adopted. Passed and to Senate. {vote_breakdown}',
    u'Read third time. Amended. {vote_breakdown}',
    u'Read third time. Amended. {vote_breakdown} To third reading.',
    u'Read third time and amended. {page}',
    u'Read third time. Refused passage. {vote_breakdown}',
    u'Read third time. Urgency clause adopted. Passed and to Assembly. {vote_breakdown}',
    u'Read third time. Amended. \(Page (?P<page>\d+)\.\) To third reading\.',
    u'Read third time, passed, and to {chamber}. {vote_breakdown}',
    u'Read third time. Urgency clause adopted. Passed. {vote_breakdown} To {chamber}.',
    u'Read third time. Urgency clause adopted. Passed. Ordered to (the )?{chamber}. {vote_breakdown}',
    u'Read third time. Passed. {vote_breakdown} {chamber}.',
    u'Read third time, passed, and to {chamber}. {vote_breakdown}',
    u'Read third time and amended. Ordered to third reading. \(Page (?P<page>\d+)\.\)',
    u'Read third time. Passed. Ordered to the {chamber}. {vote_breakdown}',
    u'Read. Adopted. {vote_breakdown} {chamber}.',
    u'Senate amendments concurred in. To enrollment. {vote_breakdown}',
    u'(Heard in committee on {month_day}\.)',
    u'Adopted and to Senate. {vote_breakdown}',
    u'Chaptered by Secretary of State.+?Chapter {sl_chapter}, Statutes of {sl_year}.',
    u'Amended. Ordered to third reading.',

    u'From committee: (?P<motion>.+?) {vote_breakdown} \({month_day}\)\.?(?P<extra>.{{,150}})',
    u'From committee: (?P<motion>.+?) {vote_breakdown} (?P<extra>.{{,150}})',
    u'From committee: (?P<motion>.+?) \({month_day}\).',
    u'From committee: (?P<motion>.+?) {vote_breakdown}',
    u"From committee chair, with author's amendments: (?P<motion>.+?)",
    # u'From committee: Do pass as amended, but first amend, and re-refer to Com. on APPR. (Ayes 8. Noes 6.)'
    u'Set for hearing {month_day}.',
    u'Assembly Rule (?P<assembly_rule>\S+) suspended. {page}',
    u'Senate concurs in Assembly amendments. {vote_breakdown} To enrollment.',
    u'Approved by Governor. \(Item veto\)',
    u'Placed on inactive file on request of Assembly Member (?P<member_name>.+?)\.',
    u'\(?Received by Desk on {month_day} pursuant to (?P<rule_citation>.+?)\.',

    u'Read and adopted. {vote_breakdown} To {chamber}\.',
    u'Adopted and to Senate. {page}',
    u'From print. May be acted upon on or after {month_day}.',
    u'Referred to {committee}.',
    u'\(Corrected {month_day}.\)',
    u'In Assembly. Concurrence in Senate amendments pending. May be considered on or after {month_day} pursuant to Assembly Rule (?P<assembly_rule>[\d\.]+).',
    u'Adopted and to Assembly. {vote_breakdown}',
    u'Senate amendments concurred in. To Engrossing and Enrolling. {vote_breakdown}.',

    u'Set, first hearing. Failed passage in committee. {vote_breakdown} Reconsideration granted.',
    u'{vote_breakdown}',
    u'Re-referred to {committee}.? pursuant to Assembly Rule (?P<assembly_rule>[\d\.]+)',
    u'Read third time. Urgency clause adopted. Passed. {vote_breakdown} Ordered to the Assembly.',
    u'Joint Rule 62\(a\) file notice suspended. {page}',
    u'Assembly amendments concurred in. {vote_breakdown} Ordered to engrossing and enrolling.',
    u'Joint Rules 28, 28.1, and 29.5 suspended in the Senate.',

    u'Joint Rule 62(a), file notice suspended. {page}',
    u'Amended, adopted, and to Senate. {page}',
    u'Enrolled. To Governor at (?P<time>.+)',
    u'Withdrawn from committee. Re-referred to {committee}',
    u'Senate amendments concurred in. To Engrossing and Enrolling.',
    u'Re-referred to {committee}.',
    u'In committee: Set, first hearing. Hearing canceled at the request of author.',
    u"From committee with author's amendments. Read second time and amended. Re-referred to {committee}.",
    u'Enrolled. To Governor at (?P<time>.+)'
    ]
patterns = [re.compile(p.format(**sub_patterns)) for p in patterns]


def main(_, abbr):
    actions_list = list(get_actions(abbr))
    actions = set(actions_list)
    print 'Total unique actions:', len(actions)

    matched = set()
    _actions = set(actions)
    for pattern in patterns:
        _matched = set(filter(pattern.search, _actions))
        matched |= _matched
        _actions -= matched
        print
        print pattern.pattern
        print 'number matched: %d' % len(_matched)

    print
    print 'number still unmatched: %d' % len(_actions)
    print 'total', len(actions_list)
    print 'percentage:', 1.0 * len(matched) / len(actions_list)
    raw_input('Press enter to continue')

    actions = list(_actions)
    while 1:
        pprint.pprint(actions[:10])

        while 1:
            inp = raw_input('Enter a regex (or enter to re-list, x to show more matches): ')
            if inp == 'x':
                pprint.pprint(list(set(matching))[:1000])
                continue
            elif inp:
                rgx = re.compile(inp)
            else:
                break
            matching = filter(rgx.search, actions)
            pprint.pprint(list(set(matching))[:10])
            print '%d actions matched.' % len(matching)


if __name__ == '__main__':
    main(*sys.argv)
