from billy import db

from django.shortcuts import render_to_response, redirect

def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x:x['name'])
    return render_to_response('downloads.html', {'states':states})


def data_zip(request, state):
    metadata = db.metadata.find_one({'_id': state})
    if not metadata or 'latest_dump_url' not in metadata:
        raise Http404
    return redirect(metadata['latest_dump_url'])
