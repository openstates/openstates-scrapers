from billy import db

from django.shortcuts import render, redirect

def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x:x['name'])
    return render(request, 'downloads.html', {'states':states})
