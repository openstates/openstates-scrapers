import json
import datetime

from billy.utils import chamber_name
from billy.site.api.feeds import EventFeed
from billy.site.api import xml

from django.template import defaultfilters
from piston.emitters import Emitter, JSONEmitter

import icalendar
import lxml.etree
from lxml.builder import E


class DateTimeAwareJSONEncoder(json.JSONEncoder):
    # We wouldn't need this if django's stupid DateTimeAwareJSONEncoder
    # used settings.DATETIME_FORMAT instead of hard coding its own
    # format string.

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return defaultfilters.date(o, 'DATETIME_FORMAT')
        elif isinstance(o, datetime.date):
            return defaultfilters.date(o, 'DATE_FORMAT')
        elif isinstance(o, datetime.time):
            return defaultfilters.date(o, 'TIME_FORMAT')

        return super(DateTimeAwareJSONEncoder, self).default(o)


class BillyJSONEmitter(JSONEmitter):
    """
    Removes private fields (keys preceded by '_') recursively and
    outputs as JSON, with datetimes converted to strings.
    """

    def render(self, request):
        cb = request.GET.get('callback', None)
        seria = json.dumps(self.construct(), cls=DateTimeAwareJSONEncoder,
                           ensure_ascii=False)

        if cb:
            return "%s(%s)" % (cb, seria)

        return seria

    def construct(self):
        return self._clean(super(BillyJSONEmitter, self).construct())

    def _clean(self, obj):
        if isinstance(obj, dict):
            # Expose the '_id' field as 'id' for certain object types
            if (obj.get('_type') in ('person',
                                     'committee',
                                     'event') and '_id' in obj):
                obj['id'] = obj['_id']

            for key, value in obj.items():
                if key.startswith('_'):
                    del obj[key]
                else:
                    obj[key] = self._clean(value)
        elif isinstance(obj, list):
            obj = [self._clean(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if key.startswith('_'):
                    del obj.__dict__[key]
                else:
                    obj.__dict__[key] = self._clean(value)
        return obj


class BillyXMLEmitter(Emitter):
    def render(self, request):
        obj = self.construct()
        if isinstance(obj, list):
            results = E.results(*[xml.render(o) for o in obj])
        else:
            results = E.results(xml.render(obj))

        return lxml.etree.tostring(results, pretty_print=True,
                                   xml_declaration=True,
                                   encoding='UTF-8')


class FeedEmitter(Emitter):
    """
    Emits an RSS feed from a list of billy 'event' objects.

    Expects a list of objects from the handler. Non-event objects will be
    ignored.
    """

    def render(self, request):
        return EventFeed()(request, self.construct())


class _vDatetime(icalendar.vDatetime):
    """
    The icalendar module outputs datetimes with VALUE=DATE,
    which breaks some calendar clients. This is a fix to
    use VALUE=DATETIME.
    """
    def __init__(self, dt):
        self.dt = dt
        self.params = icalendar.Parameters(dict(value='DATETIME'))


class ICalendarEmitter(Emitter):
    """
    Emits an iCalendar-format calendar from a list of 'event' objects.

    Expects a list of objects from the handler. Non-event objects will be
    ignored.
    """

    def render(self, request):
        cal = icalendar.Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', 'billy')

        for obj in self.construct():
            if not isinstance(obj, dict):
                continue

            if obj.get('_type') != 'event':
                # We can only serialize events
                continue

            event = icalendar.Event()

            if obj.get('all_day', False):
                event.add('dtstart', obj['when'].date())
                event['X-FUNAMBOL-ALLDAY'] = 1
                event['X-MICROSOFT-CDO-ALLDAYEVENT'] = 1
            else:
                event['dtstart'] = _vDatetime(obj['when'])

                end = obj.get('end')
                if not end:
                    end = obj['when'] + datetime.timedelta(hours=1)
                event['dtend'] = _vDatetime(end)

            if obj['type'] == 'committee:meeting':
                part = obj['participants'][0]
                comm = part['participant']

                chamber = part.get('chamber')
                if chamber:
                    comm = "%s %s" % (chamber_name(obj[obj['level']], chamber),
                                      comm)

                summary = "%s Committee Meeting" % comm
            elif obj['type'] == 'bill:action':
                summary = obj['description']
            else:
                continue

            event.add('summary', summary)
            event.add('location', obj.get('location', 'Unknown'))
            event['uid'] = obj['_id']

            status = obj.get('status')
            if status:
                event.add('status', status.upper())

            notes = obj.get('notes')
            if notes:
                event.add('description', notes)

            link = obj.get('link')
            if link:
                event.add('attach', link)

            for participant in obj['participants']:
                addr = icalendar.vCalAddress('MAILTO:noone@example.com')

                chamber = participant.get('chamber')
                if chamber:
                    cn = chamber_name(obj[obj['level']], chamber) + " "
                else:
                    cn = ""

                cn += participant['participant']

                if participant['type'] == 'committee':
                    cn += ' Committee'

                addr.params['cn'] = icalendar.vText(cn)
                #addr.params['ROLE'] = icalendar.vText('COMMITTEE')
                event.add('attendee', addr, encode=0)
                event['organizer'] = addr

            cal.add_component(event)

        return cal.as_string()
