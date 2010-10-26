from __future__ import with_statement
import os
import uuid

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.scrape import Scraper, FiftystatesObject, JSONDateEncoder


class EventScraper(Scraper):

    scraper_type = 'events'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../../schemas/event.json')

        with open(schema_path) as f:
            schema = json.load(f)

        return schema

    def scrape(self, chamber, session):
        raise NotImplementedError("EventScrapers must define a scrape method")

    def save_event(self, event):
        event['state'] = self.state

        self.log("save_event %s %s: %s" % (event['when'],
                                           event['type'],
                                           event['description']))

        self.validate_json(event)

        filename = "%s.json" % str(uuid.uuid1())
        with open(os.path.join(self.output_dir, "events", filename), 'w') as f:
            json.dump(event, f, cls=JSONDateEncoder)


class Event(FiftystatesObject):
    def __init__(self, session, when, type,
                 description, end=None, **kwargs):
        super(Event, self).__init__('event', **kwargs)
        self['session'] = session
        self['when'] = when
        self['type'] = type
        self['description'] = description
        self['end'] = end
        self['participants'] = []
        self.update(kwargs)

    def add_participant(self, type, participant, **kwargs):
        kwargs.update({'type': type, 'participant': participant})
        self['participants'].append(kwargs)
