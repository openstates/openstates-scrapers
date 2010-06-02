import re

from fiftystates.backend import db, metadata

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response

import pymongo


def index(request):
    raise Http404


def state_index(request, state):
    meta = metadata(state)
    if not meta:
        raise Http404

    recent_bills = db.bills.find({'state': state.lower()}).sort(
        'created_at', pymongo.DESCENDING).limit(20)

    current_session = meta['sessions'][-1]

    upper = db.legislators.find({
            'roles': {'$elemMatch':
                          {'state': state,
                           'session': current_session,
                           'chamber': 'upper',
                           'type': 'member',
                           'district': {'$ne': '22'}}}}).sort('last_name')

    lower = db.legislators.find({
            'roles': {'$elemMatch':
                          {'state': state,
                           'session': current_session,
                           'chamber': 'lower',
                           'type': 'member'}}}).sort('last_name')

    return render_to_response('state_index.html',
                              {'recent_bills': recent_bills,
                               'upper': list(upper),
                               'lower': list(lower),
                               'metadata': meta})


def bill(request, state, session, chamber, id):
    chamber = chamber.lower()

    if chamber in ('house', 'assembly'):
        chamber = 'lower'
    elif chamber == 'senate':
        chamber = 'lower'

    id = id.replace('-', ' ')
    bill = db.bills.find_one(dict(state=state.lower(),
                                  session=session,
                                  chamber=chamber,
                                  bill_id=re.compile('^%s' % id,
                                                     re.IGNORECASE)))
    if not bill:
        raise Http404

    return render_to_response('bill.html', {'bill': bill})


def legislator(request, id):
    leg = db.legislators.find_one({'_all_ids': id})
    if not leg:
        raise Http404

    for role in leg['roles']:
        if role['type'] == 'member':
            leg['active_role'] = role
            break

    return render_to_response('legislator.html', {'leg': leg})
