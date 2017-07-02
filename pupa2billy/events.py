import datetime
from .utils import get_json
from billy.scrape.events import EventScraper, Event


def parse_datetime(timestamp):
    dt = datetime.datetime.strptime(timestamp[:-6], '%Y-%m-%dT%H:%M:%S')
    return dt


class PupaEventScraper(EventScraper):

    def __init__(self, *args, **kwargs):
        self.jurisdiction = kwargs.pop('jurisdiction')
        super(PupaEventScraper, self).__init__(*args, **kwargs)

    def scrape(self, **kwargs):
        for event in get_json(self.jurisdiction, 'event'):
            self.process_event(event)

    def process_event(self, data):
        session = self.metadata['terms'][-1]['name']

        event = Event(session=session,
                      when=parse_datetime(data['start_date']),
                      type='committee:meeting',
                      description=data['description'],
                      # timezone=data['timezone'],
                      location=data['location']['name'],
                      end=data['end_date'])

        # TODO: participants, documents, related_bills

        for source in data['sources']:
            event.add_source(source['url'])

        event.update(**data['extras'])

        self.save_event(event)
