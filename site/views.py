from billy import db

from django.shortcuts import render_to_response, redirect

def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x:x['name'])
    return render_to_response('downloads.html', {'states':states})
