from billy import db, fs

from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect

import gridfs


def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x:x['_id'])
    return render_to_response('downloads.html', {'states':states})


def data_zip(request, state):
    metadata = db.metadata.find_one({'_id': state})
    if not metadata or 'latest_dump_url' not in metadata:
        raise Http404
    return redirect(metadata['latest_dump_url'])


def document(request, id):
    try:
        doc = fs.get(id)
    except gridfs.NoFile:
        raise Http404

    return HttpResponse(doc.read(), mimetype=doc.content_type)


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
