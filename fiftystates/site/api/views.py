from fiftystates.backend import fs

from django.http import HttpResponse, Http404

import gridfs


def document(request, id):
    try:
        doc = fs.get(id)
    except gridfs.NoFile:
        raise Http404

    return HttpResponse(doc.read(), mimetype=doc.content_type)
