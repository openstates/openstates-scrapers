from billy import db

from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response


def legislator_preview(request, id):
    """
    A table of basic legislator information for use with as an embedded
    preview in Google Refine (especially w/ reconciliation).
    """
    legislator = db.legislators.find_one({'_id': id})

    if not legislator:
        return Http404

    return render_to_response('legislator_preview.html',
                              {'legislator': legislator})
