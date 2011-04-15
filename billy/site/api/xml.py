import lxml.etree
from lxml.builder import E


def render(obj):
    if obj['_type'] == 'bill':
        return render_bill(obj)
    return None


def render_bill(bill):
    if 'actions' not in bill:
        return render_short_bill(bill)
    else:
        return render_full_bill(bill)


def render_short_bill(bill):
    return E.bill(
        E.state(bill['state']),
        E.session(bill['session']),
        E.chamber(bill['chamber']),
        E.bill_id(bill['bill_id']),
        E.title(bill['title']),
        *[E.type(t) for t in bill['type']],
        created_at=str(bill['created_at']),
        updated_at=str(bill['updated_at'])
    )


def render_full_bill(bill):
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
                     for s in bill.get('sponsors', [])]),

        E.actions(*[action(a) for a in bill.get('actions', [])]),
        E.votes(*[vote(v) for v in bill.get('votes', [])]),
        E.subjects(*[E.subject(s) for s in bill.get('subjects', [])]),

        E.versions(*[E.version(href=v['url'], name=v['name'])
                     for v in bill.get('versions', [])]),

        E.sources(*[E.source(href=s['url'], retrieved=str(s['retrieved']))
                    for s in bill.get('sources', [])]),

        *[E.type(t) for t in bill['type']],

        updated_at=str(bill['updated_at']),
        created_at=str(bill['created_at'])
    )
