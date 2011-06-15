import datetime

import lxml.etree
from lxml.builder import E


def _date(d):
    if isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%dT%H:%M:%S")
    elif isinstance(d, datetime.date):
        return d.strftime("%Y-%m-%d")

    raise ValueError("expected date or datetime")


def _bool(b):
    return str(b).lower()


def render(obj):
    try:
        renderer = {'bill': render_bill,
                    'person': render_legislator,
                    'legislator': render_legislator,
                    'committee': render_committee,
                    'metadata': render_metadata,
                    'event': render_event}[obj['_type']]
    except KeyError:
        raise ValueError(
            "don't know how to serialize object of type '%s'" % obj['_type'])

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
            *[E.source(href=s['url'])
              for s in obj['sources']]))

    return elem


def render_bill(bill):
    if 'actions' not in bill:
        return render_short_bill(bill)
    else:
        return render_full_bill(bill)


def render_short_bill(bill):
    return E.bill(
        E.level(bill['level']),
        E.country(bill['country']),
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
            return E.avote(name=av['name'], leg_id=av['leg_id'], type=type)
        else:
            return E.avote(name=av['name'], type=type)

    def vote(v):
        avotes = [avote(av, 'yes') for av in v['yes_votes']]
        avotes.extend([avote(av, 'no') for av in v['no_votes']])
        avotes.extend([avote(av, 'other') for av in v['other_votes']])

        return E.vote(
            E.motion(v['motion']),
            *avotes,

            date=_date(v['date']),
            chamber=v['chamber'],
            id=v['vote_id'],
            type=v.get('type', '') or '',
            yes_count=str(v['yes_count']),
            no_count=str(v['no_count']),
            other_count=str(v['other_count']),
            passed=_bool(v['passed'])
        )

    elem = render_short_bill(bill)
    elem.extend([
        E.alternate_titles(*[E.title(t) for t in bill.get(
            'alternate_titles', [])]),

        E.sponsors(*[E.sponsor(s['name'], id=s['leg_id'] or '', type=s['type'])
                     for s in bill.get('sponsors', [])]),

        E.actions(*[action(a) for a in bill.get('actions', [])]),
        E.votes(*[vote(v) for v in bill.get('votes', [])]),
        E.subjects(*[E.subject(s) for s in bill.get('subjects', [])]),

        E.versions(*[E.version(v['name'], href=v['url'])
                     for v in bill.get('versions', [])]),

        E.documents(*[E.document(d['name'], href=d['url'])
                      for d in bill.get('documents', [])]),
        ]
    )

    return elem


def render_legislator(leg):
    if 'roles' not in leg:
        return render_short_legislator(leg)
    else:
        return render_full_legislator(leg)


def render_short_legislator(leg):
    elem = E.legislator(
        E.level(leg['level']),
        E.country(leg['country']),
        E.state(leg['state']),
        E.first_name(leg['first_name']),
        E.last_name(leg['last_name']),
        E.full_name(leg['full_name']),
        E.middle_name(leg['middle_name']),
        E.suffixes(leg['suffixes']),

        E.transparencydata_id(leg.get('transparencydata_id', '') or ''),
        E.votesmart_id(leg.get('votesmart_id', '') or ''),
        E.nimsp_candidate_id(leg.get('nimsp_candidate_id', '') or ''),
        E.photo_url(leg.get('photo_url', '')),

        id=leg['leg_id']
    )

    if leg.get('active'):
        elem.append(E.active('true'))
        for key in ('chamber', 'district', 'party'):
            value = leg.get(key)
            if value:
                elem.append(E(key, value))
    else:
        elem.append(E.active('false'))

    return elem


def render_full_legislator(leg):
    def role(r):
        children = []
        kwargs = {}

        if r['type'] == 'committee member':
            children.append(E.committee(
                r['committee'],
                id=r.get('committee_id', '') or ''))

        for optional_attr in ('party', 'start_date', 'end_date',
                              'chamber'):
            value = r.get(optional_attr)
            if isinstance(value, datetime.date):
                kwargs[optional_attr] = _date(value)
            elif value:
                kwargs[optional_attr] = str(value)

        return E.role(
            *children,
            type=r['type'],
            term=r['term'],
            **kwargs
        )

    old_terms = []
    if leg.get('old_roles'):
        for key, value in leg.get('old_roles').iteritems():
            old_terms.append(E.term(
                *[role(r) for r in value],
                name=key))

    elem = render_short_legislator(leg)
    elem.extend([
        E.roles(*[role(r) for r in leg.get('roles', [])]),
        E.old_roles(*old_terms),
    ])

    return elem


def render_committee(comm):
    if 'members' not in comm:
        return render_short_committee(comm)
    else:
        return render_full_committee(comm)


def render_short_committee(comm):
    kwargs = {}
    pid = comm.get('parent_id')
    if pid:
        kwargs['parent_id'] = pid

    return E.committee(
        E.level(comm['level']),
        E.country(comm['country']),
        E.state(comm['state']),
        E.chamber(comm['chamber']),
        E.name(
            E.committee_name(comm['committee']),
            E.subcommittee_name(comm.get('subcommittee', '') or ''),
        ),

        id=comm['_id'],
        **kwargs
    )


def render_full_committee(comm):
    def member(m):
        kwargs = {}
        leg_id = kwargs.get('leg_id')
        if leg_id:
            kwargs['id'] = leg_id
        return E.member(m['name'], role=m['role'], **kwargs)

    elem = render_short_committee(comm)
    elem.append(E.members(*[member(m) for m in comm['members']]))

    return elem


def render_metadata(meta):
    def session(s):
        args = []
        try:
            details = meta['session_details'][s]
            for key in ('type', 'start_date', 'end_date'):
                value = details.get(key)
                if value:
                    if isinstance(value, datetime.date):
                        args.append(E(key, _date(value)))
                    else:
                        args.append(E(key, str(value)))
        except KeyError:
            pass

        return E.session(E.name(s), *args)

    elem = E.metadata(
        E.level(meta['level']),
        E.state_name(meta['name']),
        E.state_abbreviation(meta['abbreviation']),
        E.legislature_name(meta['legislature_name']),
        E.latest_update(_date(meta['latest_update'])),
    )

    for chamber in ('upper', 'lower'):
        if ('%s_chamber_name' % chamber) not in meta:
            # for unicams
            continue

        elem.append(E.chamber(
            E.type(chamber),
            E.name(meta[chamber + '_chamber_name']),
            E.title(meta[chamber + '_chamber_title']),
            E.term(str(meta[chamber + '_chamber_term'])),
        ))

    terms = E.terms()
    for term in meta['terms']:
        terms.append(E.term(
            E.name(term['name']),
            E.start_year(str(term['start_year'])),
            E.end_year(str(term['end_year'])),
            *[session(s) for s in term['sessions']]
        ))

    elem.append(terms)

    return elem


def render_event(ev):
    def participant(p):
        kwargs = {}
        chamber = p.get('chamber')
        if chamber:
            kwargs['chamber'] = chamber

        return E.participant(
            p['participant'],
            type=p['type'],
            **kwargs
        )

    if ev['end']:
        end = E.end(_date(ev['end']))
    else:
        end = E.end()

    extra = []
    if 'link' in ev:
        extra.append(E.link(href=ev['link']))

    return E.event(
        E.level(ev['level']),
        E.country(ev['country']),
        E.state(ev['state']),
        E.session(ev['session']),
        E.type(ev['type']),
        E.when(_date(ev['when'])),
        end,
        E.location(ev['location']),
        E.all_day(_bool(ev.get('all_day', False))),
        E.description(ev['description']),
        E.notes(ev.get('notes', '') or ''),
        E.participants(*[participant(p) for p in ev['participants']]),
        *extra,
        id=ev['_id']
    )
