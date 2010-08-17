from fiftystates.site.api.models import LogEntry

from piston.emitters import JSONEmitter, XMLEmitter


class LoggingJSONEmitter(JSONEmitter):
    def render(self, request):
        LogEntry.objects.create(
            caller_key=request.apikey.key,
            method=self.handler.__class__.__name__,
            query_string=request.META['QUERY_STRING'],
        )
        return super(LoggingJSONEmitter, self).render(request)

class LoggingXMLEmitter(XMLEmitter):
    def render(self, request):
        LogEntry.objects.create(
            caller_key=request.apikey.key,
            method=self.handler.__class__.__name__,
            query_string=request.META['QUERY_STRING'],
        )
        return super(LoggingXMLEmitter, self).render(request)
