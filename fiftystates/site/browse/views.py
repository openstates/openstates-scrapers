import re
import random
from collections import defaultdict

from fiftystates.backend import db, metadata

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.views.decorators.cache import never_cache
from django.shortcuts import render_to_response, redirect
from django.utils.datastructures import SortedDict

import pymongo

def keyfunc(obj):
    try:
        return int(obj['district'])
    except ValueError:
        return obj['district']

def state_index(request, state):
    meta = metadata(state)
    if not meta:
        raise Http404

    context = {}
    context['metadata'] = SortedDict(sorted(meta.items()))

    # counts
    context['upper_bill_count'] = db.bills.find({'state':state,
                                                 'chamber': 'upper'}).count()
    context['lower_bill_count'] = db.bills.find({'state':state,
                                                 'chamber': 'lower'}).count()
    context['bill_count'] = context['upper_bill_count'] + context['lower_bill_count']
    context['ns_bill_count'] = db.bills.find({'state': state,
                                           'sources': {'$size': 0}}).count()

    # types
    types = defaultdict(int)
    action_types = defaultdict(int)
    total_actions = 0

    for bill in db.bills.find({'state': state}, {'type':1, 'actions.type': 1}):
        for t in bill['type']:
            types[t] += 1
        for a in bill['actions']:
            for at in a['type']:
                action_types[at] += 1
                total_actions += 1
    context['types'] = dict(types)
    context['action_types'] = dict(action_types)
    if total_actions:
        context['action_cat_percent'] = ((total_actions-action_types['other'])/
                                         float(total_actions)*100)

    # legislators
    context['upper_leg_count'] = db.legislators.find({'state':state,
                                                  'chamber':'upper'}).count()
    context['lower_leg_count'] = db.legislators.find({'state':state,
                                                  'chamber':'lower'}).count()
    context['leg_count'] = context['upper_leg_count'] + context['lower_leg_count']
    context['ns_leg_count'] = db.legislators.find({'state': state,
                             'sources': {'$size': 0}}).count()
    context['missing_pvs'] = db.legislators.find({'state': state,
                             'votesmart_id': {'$exists':False}}).count()
    context['missing_nimsp'] = db.legislators.find({'state': state,
                             'nimsp_candidate_id': {'$exists':False}}).count()

    # committees
    context['upper_com_count'] = db.committees.find({'state':state,
                                                  'chamber':'upper'}).count()
    context['lower_com_count'] = db.committees.find({'state':state,
                                                  'chamber':'lower'}).count()
    context['joint_com_count'] = db.committees.find({'state':state,
                                                  'chamber':'joint'}).count()
    context['com_count'] = (context['upper_com_count'] +
                            context['lower_com_count'] +
                            context['joint_com_count'])
    context['ns_com_count'] = db.committees.find({'state': state,
                             'sources': {'$size': 0}}).count()

    return render_to_response('state_index.html', context)

@never_cache
def random_bill(request, state):
    bill = None
    while not bill:
        _id = '%sB%06d' % (state.upper(),
                           random.randint(1, db.bills.find({'state':state.lower()})))
        bill = db.bills.findone({'_id':_id})

    return render_to_response('bill.html', {'bill': bill})

def bill(request, state, session, id):
    id = id.replace('-', ' ')
    bill = db.bills.find_one(dict(state=state.lower(),
                                  session=session,
                                  bill_id=re.compile('^%s' % id,
                                                     re.IGNORECASE)))
    if not bill:
        raise Http404

    return render_to_response('bill.html', {'bill': bill})


def legislator(request, id):
    leg = db.legislators.find_one({'_all_ids': id})
    print id
    if not leg:
        raise Http404
    return render_to_response('legislator.html', {'leg': leg,
                                              'metadata': metadata(leg['state'])})
