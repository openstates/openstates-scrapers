import lxml.etree
from lxml.builder import E


def bill_to_xml(bill):
    def action(a):
        return E.action(
            E.text(a['action']),
            *[E.type(t) for t in a['type']],
            date=str(a['date']),
            actor=a['actor']
        )

    def avote(av, type):
        if av['leg_id']:
            return E.avote(name=sv, leg_id=a['leg_id'], type=type)
        else:
            return E.avote(name=sv, type=type)

    def vote(v):
        avotes = [avote(av, 'yes') for av in v['yes_votes']]
        avotes.extend([avote(av, 'no') for av in v['no_votes']])
        avotes.extend([avote(av, 'other') for av in v['other_votes']])

        return E.vote(
            E.motion(v['motion']),
            *avotes,

            date=str(v['date']),
            chamber=v['chamber'],
            id=v['id'],
            type=v['type'],
            yes_count=str(v['yes_count']),
            no_count=str(v['no_count']),
            other_count=str(v['other_count']),
            passed=str(v['passed']).lower()
        )

    return E.bill(
        E.state(bill['state']),
        E.session(bill['session']),
        E.chamber(bill['chamber']),
        E.bill_id(bill['bill_id']),
        E.title(bill['title']),

        E.alternate_titles(*[E.title(t) for t in bill.get(
            'alternate_titles', [])]),

        E.sponsors(*[E.sponsor(s['name'], id=s['leg_id'] or '', type=s['type'])
                     for s in bill['sponsors']]),

        E.actions(*[action(a) for a in bill['actions']]),
        E.votes(*[vote(v) for v in bill['votes']]),
        E.subjects(*[E.subject(s) for s in bill.get('subjects', [])]),

        E.versions(*[E.version(href=v['url'], name=v['name'])
                     for v in bill['versions']]),

        E.sources(*[E.source(href=s['url'], retrieved=str(s['retrieved']))
                    for s in bill['sources']]),

        *[E.type(t) for t in bill['type']],

        updated_at=str(bill['updated_at']),
        created_at=str(bill['created_at'])
    )
