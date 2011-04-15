import datetime

import lxml.etree
from lxml.builder import E

def _date(d):
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%d-%mT%H:%M:%S")
    elif isinstance(d, datetime.date):
        return d.strftime("%Y-%d-%m")

    raise ValueError("expected date or datetime")


def render(obj):
    if obj['_type'] == 'bill':
        return render_bill(obj)
    elif obj['_type'] in ('person', 'legislator'):
        return render_legislator(obj)
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
        created_at=_date(bill['created_at']),
        updated_at=_date(bill['updated_at'])
    )


def render_full_bill(bill):
    def action(a):
        return E.action(
            E.text(a['action']),
            *[E.type(t) for t in a['type']],
            date=_date(a['date']),
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

            date=_date(v['date']),
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

        E.sources(*[E.source(href=s['url'], retrieved=_date(s['retrieved']))
                    for s in bill.get('sources', [])]),

        *[E.type(t) for t in bill['type']],

        updated_at=_date(bill['updated_at']),
        created_at=_date(bill['created_at'])
    )


def render_legislator(leg):
    def role(r):
        children = []
        kwargs = {}

        if r['type'] == 'committee member':
            children.append(E.committee(
                r['committee'],
                id=r['committee_id']))

        for optional_attr in ('party', 'start_date', 'end_date'):
            value = r.get(optional_attr)
            if value:
                kwargs[optional_attr] = str(value)

        return E.role(
            *children,
            type=r['type'],
            term=r['term'],
            chamber=r['chamber'],
            **kwargs
        )

    old_terms = []
    for key, value in leg.get('old_roles', []):
        old_terms.append(E.term(
            *[role(r) for r in value]))

    return E.legislator(
        E.state(leg['state']),
        E.first_name(leg['first_name']),
        E.last_name(leg['last_name']),
        E.full_name(leg['full_name']),
        E.middle_name(leg['middle_name']),
        E.suffixes(leg['suffixes']),
        E.roles(*[role(r) for r in leg['roles']]),
        E.old_roles(*old_terms),

        E.transparencydata_id(leg.get('transparencydata_id', '')),
        E.votesmart_id(leg.get('votesmart_id', '')),
        E.nimsp_candidate_id(leg.get('nimsp_candidate_id', '')),
        E.photo_url(leg.get('photo_url', '')),

        E.sources(*[E.source(href=s['url'], retrieved=_date(s['retrieved']))
                    for s in leg.get('sources', [])]),

        created_at=_date(leg['created_at']),
        updated_at=_date(leg['updated_at']),
        id=leg['leg_id']
    )
