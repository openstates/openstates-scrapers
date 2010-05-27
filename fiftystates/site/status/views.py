from fiftystates.site.status.models import StateStatus

from django.conf import settings
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response


def status_index(request):
    statuses = StateStatus.objects.all().order_by('state')
    return render_to_response('status/index.html',
                              {'statuses': statuses},
                              context_instance=RequestContext(request))

def map_svg(request):
    from svgmaps import colorized_svg
    from collections import defaultdict

    mapping = defaultdict(list)

    for s in StateStatus.objects.all():
        if s.repositories.count() == 0:
            if s.completeness() < 0.01:
                color = '#bbbbbb'
            elif s.completeness() < 0.33:
                color = '#99f457'
            elif s.completeness() < 0.66:
                color = '#46c024'
            elif s.completeness() < 0.90:
                color = '#336e07'
            else:
                color = '#00ff00'
        else:
            if s.completeness() < 0.01:
                color = '#a0a0a0'
            elif s.completeness() < 0.33:
                color = '#57daf4'
            elif s.completeness() < 0.66:
                color = '#2484c0'
            elif s.completeness() < 0.90:
                color = '#07396e'
            else:
                color = '#0000ff'
        mapping[color].append(s.state.upper())

    svg = colorized_svg(mapping, infile=settings.STATUS_SVG_FILE)

    return HttpResponse(svg, mimetype="image/svg+xml")
