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
    renderer = {'bill': render_bill,
                'person': render_legislator,
                'legislator': render_legislator,
                'committee': render_committee}[obj['_type']]

    elem = renderer(obj)

    # Append some universal attributes and elements
    if 'created_at' in obj:
        elem.attrib['created_at'] = _date(obj['created_at'])
    if 'updated_at' in obj:
        elem.attrib['updated_at'] = _date(obj['updated_at'])
    if 'id' in obj:
        elem.attrib['id'] = obj['id']
    if 'sources' in obj:
        elem.append(E.sources(
            *[E.source(href=s['url'], retrieved=_date(s['retrieved']))
              for s in obj['sources']]))

    return elem


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
        *[E.type(t) for t in bill['type']]
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

        *[E.type(t) for t in bill['type']]
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

        id=leg['leg_id']
    )


def render_committee(comm):
    def member(m):
        kwargs = {}
        if 'leg_id' in m:
            kwargs['id'] = m['leg_id']
        return E.member(m['name'], role=m['role'], **kwargs)

    kwargs = {}
    pid = comm.get('parent_id')
    if pid:
        kwargs['parent_id'] = pid

    return E.committee(
        E.state(comm['state']),
        E.chamber(comm['chamber']),
        E.name(E.committee_name(comm['committee']),
               E.subcommittee_name(comm.get('subcommittee', '') or '')),
        E.subcommittee_name(comm.get('subcommittee', '') or ''),
        E.members(*[member(m) for m in comm['members']]),

        id=comm['_id'],
        **kwargs
    )
