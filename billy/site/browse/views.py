import random
from collections import defaultdict

from billy import db
from billy.utils import metadata

from django.http import Http404
from django.views.decorators.cache import never_cache
from django.shortcuts import render_to_response
from django.utils.datastructures import SortedDict


def keyfunc(obj):
    try:
        return int(obj['district'])
    except ValueError:
        return obj['district']


def browse_index(request, template='billy/index.html'):
    rows = []
    total_missing_ids = 0
    total_active = 0

    for meta in list(db.metadata.find()) + [{'_id':'total', 'name':'total'}]:
        row = {}
        row['id'] = meta['_id']
        row['name'] = meta['name']
        counts = db.counts.find_one({'_id': row['id']})
        if counts:
            counts = counts['value']
            row['bills'] = counts['bills']
            row['votes'] = counts['votes']
            row['versions'] = counts['versions']
            if counts['actions']:
                row['typed_actions'] = (float(counts['categorized']) /
                                        counts['actions_this_term'] * 100)
            if counts['bills']:
                row['subjects'] = (float(counts['subjects']) /
                                   counts['bills'] * 100)
            if counts['sponsors']:
                row['sponsor_ids'] = (float(counts['idd_sponsors']) /
                                      counts['sponsors'] * 100)
            if counts['voters']:
                row['voter_ids'] = (float(counts['idd_voters']) /
                                    counts['voters'] * 100)

        if row['id'] != 'total':
            level = meta['level']
            s_spec = {'level': level, level: row['id']}
            row['bill_types'] = len(db.bills.find(s_spec).distinct('type')) > 1
            row['legislators'] = db.legislators.find(s_spec).count()
            row['committees'] = db.committees.find(s_spec).count()
            row['events'] = db.events.find(s_spec).count()
            id_counts = _get_leg_id_stats(level, row['id'])
            active_legs = db.legislators.find({'level': level,
                                               level: row['id'],
                                               'active': True}).count()

            if not active_legs:
                row['external_ids'] = 0
            else:
                missing_ids = float(id_counts['missing_pvs'] +
                                    id_counts['missing_tdata'])
                row['external_ids'] = (1 - (missing_ids /
                                            (active_legs * 2))) * 100
                total_missing_ids += missing_ids
                total_active += active_legs

            missing_bill_sources = db.bills.find({'level': level,
                                                  level: row['id'],
                                              'sources': {'$size': 0}}).count()
            missing_leg_sources = db.legislators.find({'level': level,
                                                       level: row['id'],
                                              'sources': {'$size': 0}}).count()
            row['missing_sources'] = ''
            if missing_bill_sources:
                row['missing_sources'] += 'bills'
            if missing_leg_sources:
                row['missing_sources'] += ' legislators'
        else:
            row['bill_types'] = 'n/a'
            row['legislators'] = db.legislators.find().count()
            row['committees'] = db.committees.find().count()
            row['events'] = db.events.find().count()

        rows.append(row)

    rows.sort(key=lambda x: x['id'] if x['id'] != 'total' else 'zz')

    # set total external ids
    rows[-1]['external_ids'] = (1 - (total_missing_ids /
                                     (total_active * 2))) * 100

    return render_to_response(template, {'rows': rows})


def _bill_stats_for_session(level, abbr, session):
    context = {}
    context['upper_bill_count'] = db.bills.find({'level': level,
                                                 level: abbr,
                                                 'session': session,
                                                 'chamber': 'upper'}).count()
    context['lower_bill_count'] = db.bills.find({'level': level,
                                                 level: abbr,
                                                 'session': session,
                                                 'chamber': 'lower'}).count()
    context['bill_count'] = (context['upper_bill_count'] +
                             context['lower_bill_count'])
    context['ns_bill_count'] = db.bills.find({'level': level,
                                              level: abbr,
                                              'session': session,
                                           'sources': {'$size': 0}}).count()
    types = defaultdict(int)
    action_types = defaultdict(int)
    total_actions = 0
    versions = 0

    for bill in db.bills.find({'level': level, level: abbr,
                               'session': session},
                              {'type': 1, 'actions.type': 1, 'versions': 1}):
        for t in bill['type']:
            types[t] += 1
        for a in bill['actions']:
            for at in a['type']:
                action_types[at] += 1
                total_actions += 1
        versions += len(bill.get('versions', []))
    context['versions'] = versions

    context['types'] = dict(types)
    context['action_types'] = dict(action_types)
    if total_actions:
        context['action_cat_percent'] = ((total_actions -
                                          action_types['other']) /
                                         float(total_actions) * 100)

    return context


def _get_leg_id_stats(level, abbr):
    context = {}
    context['missing_pvs'] = db.legislators.find({'level': level,
                             level: abbr,
                             'active': True,
                             'votesmart_id': {'$exists': False}}).count()
    context['missing_tdata'] = db.legislators.find({'level': level,
         level: abbr, 'active': True,
         'transparencydata_id': {'$exists': False}}).count()
    return context


def overview(request, abbr):
    meta = metadata(abbr)
    if not meta:
        raise Http404

    context = {}
    context['metadata'] = SortedDict(sorted(meta.items()))

    # types
    latest_session = meta['terms'][-1]['sessions'][-1]
    context['session'] = latest_session

    level = meta['level']

    context.update(_bill_stats_for_session(level, abbr, latest_session))

    # legislators
    context['upper_leg_count'] = db.legislators.find({'level': level,
                                                      level: abbr,
                                                      'active': True,
                                                  'chamber': 'upper'}).count()
    context['lower_leg_count'] = db.legislators.find({'level': level,
                                                      level: abbr,
                                                      'active': True,
                                                  'chamber': 'lower'}).count()
    context['leg_count'] = (context['upper_leg_count'] +
                            context['lower_leg_count'])
    context['inactive_leg_count'] = db.legislators.find({'level': level,
                                                         level: abbr,
                                                     'active': False}).count()
    context['ns_leg_count'] = db.legislators.find({'level': level,
                             level: abbr,
                             'active': True,
                             'sources': {'$size': 0}}).count()
    context.update(_get_leg_id_stats(level, abbr))

    # committees
    context['upper_com_count'] = db.committees.find({'level': level,
                                                     level: abbr,
                                                  'chamber': 'upper'}).count()
    context['lower_com_count'] = db.committees.find({'level': level,
                                                     level: abbr,
                                                  'chamber': 'lower'}).count()
    context['joint_com_count'] = db.committees.find({'level': level,
                                                     level: abbr,
                                                  'chamber': 'joint'}).count()
    context['com_count'] = (context['upper_com_count'] +
                            context['lower_com_count'] +
                            context['joint_com_count'])
    context['ns_com_count'] = db.committees.find({'level': level,
                                                  level: abbr,
                             'sources': {'$size': 0}}).count()

    return render_to_response('billy/state_index.html', context)


def bills(request, abbr):
    meta = metadata(abbr)
    level = meta['level']
    if not meta:
        raise Http404

    sessions = []
    for term in meta['terms']:
        for session in term['sessions']:
            stats = _bill_stats_for_session(level, abbr, session)
            stats['session'] = session
            sessions.append(stats)

    return render_to_response('billy/bills.html',
                              {'sessions': sessions, 'metadata': meta})


@never_cache
def random_bill(request, abbr):
    meta = metadata(abbr)
    if not meta:
        raise Http404

    level = meta['level']
    latest_session = meta['terms'][-1]['sessions'][-1]

    spec = {'level': level, level: abbr.lower(), 'session': latest_session}

    count = db.bills.find(spec).count()
    bill = db.bills.find(spec)[random.randint(0, count - 1)]

    return render_to_response('billy/bill.html', {'bill': bill})


def bill(request, abbr, session, id):
    level = metadata(abbr)['level']
    bill = db.bills.find_one({'level': level, level: abbr,
                              'session':session, 'bill_id':id.upper()})
    if not bill:
        raise Http404

    return render_to_response('billy/bill.html', {'bill': bill})


def legislators(request, abbr):
    meta = metadata(abbr)
    level = metadata(abbr)['level']

    upper_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                      'active': True, 'chamber': 'upper'})
    lower_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                      'active': True, 'chamber': 'lower'})
    inactive_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                         'active': False})
    upper_legs = sorted(upper_legs, key=keyfunc)
    lower_legs = sorted(lower_legs, key=keyfunc)
    inactive_legs = sorted(inactive_legs, key=lambda x: x['last_name'])

    return render_to_response('billy/legislators.html', {
        'upper_legs': upper_legs,
        'lower_legs': lower_legs,
        'inactive_legs': inactive_legs,
        'metadata': meta,
    })


def legislator(request, id):
    leg = db.legislators.find_one({'_all_ids': id})
    if not leg:
        raise Http404

    meta = metadata(leg[leg['level']])

    return render_to_response('billy/legislator.html', {'leg': leg,
                                                        'metadata': meta})


def committees(request, abbr):
    meta = metadata(abbr)
    level = metadata(abbr)['level']

    upper_coms = db.committees.find({'level': level, level: abbr.lower(),
                                     'chamber': 'upper'})
    lower_coms = db.committees.find({'level': level, level: abbr.lower(),
                                      'chamber': 'lower'})
    joint_coms = db.committees.find({'level': level, level: abbr.lower(),
                                      'chamber': 'joint'})
    upper_coms = sorted(upper_coms)
    lower_coms = sorted(lower_coms)
    joint_coms = sorted(joint_coms)

    return render_to_response('billy/committees.html', {
        'upper_coms': upper_coms,
        'lower_coms': lower_coms,
        'joint_coms': joint_coms,
        'metadata': meta,
    })
