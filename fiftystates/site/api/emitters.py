import json
import datetime

from fiftystates.site.api.feeds import EventFeed

from django.core.serializers.json import DateTimeAwareJSONEncoder
from piston.emitters import Emitter, JSONEmitter

import icalendar


class OpenStateJSONEmitter(JSONEmitter):
    """
    Removes private fields (keys preceded by '_') recursively and
    outputs as JSON, with datetimes converted to strings.
    """

    def construct(self):
        return self._clean(super(OpenStateJSONEmitter, self).construct())

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


class FeedEmitter(Emitter):
    """
    Emits an RSS feed from a list of Open State 'event' objects.

    Expects a list of Open State objects from the handler. Non-event
    objects will be ignored.
    """

    def render(self, request):
        return EventFeed()(request, self.construct())


class ICalendarEmitter(Emitter):
    """
    Emits an iCalendar-format calendar from a list of Open State 'event'
    object.

    Expects a list of Open State objects from the handler. Non-event
    objects will be ignored.
    """

    def render(self, request):
        cal = icalendar.Calendar()
        for obj in self.construct():
            if obj.get('_type') != 'event':
                # We can only serialize events
                continue

            event = icalendar.Event()

            if obj['type'] == 'committee:meeting':
                summary = "%s Committee Meeting" % (
                    obj['participants'][0]['participant'])
                event.add('dtstart', obj['when'])
            elif obj['type'] == 'bill:action':
                summary = obj['description']
                event.add('dtstart', obj['when'].date())
            else:
                continue

            event.add('summary', summary)

            end = obj.get('end')
            if not end:
                end = obj['when'] + datetime.timedelta(hours=1)
            event.add('dtend', end)

            event.add('location', obj.get('location', 'Unknown'))
            event['uid'] = obj['_id']

            for participant in obj['participants']:
                addr = icalendar.vCalAddress('MAILTO:noone@example.com')

                cn = participant['participant']

                if participant['type'] == 'committee':
                    cn += ' Committee'

                addr.params['cn'] = icalendar.vText(cn)
                #addr.params['ROLE'] = icalendar.vText('COMMITTEE')
                event.add('attendee', addr, encode=0)
                event['organizer'] = addr

            cal.add_component(event)

        return cal.as_string()
