import re

from fiftystates.backend import db

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response


def index(request):
    raise Http404


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
