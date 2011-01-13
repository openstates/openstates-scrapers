from fiftystates.backend import db

from django.contrib.syndication.views import Feed

import pymongo


class EventFeed(Feed):
    title = "OpenStates Event Feed"
    link = '/api/v1/events.rss'

    def get_object(self, request, events=[]):
        return events

    def items(self, obj):
        return [item for item in obj if item.get('_type') == 'event']

    def item_description(self, item):
        return item['description']

    def item_title(self, item):
        return item['description']

    def item_guid(self, item):
        return 'http://openstates.sunlightlabs.com/api/v1/events/%s/' % (
            item['_id'])

    def item_author_name(self, item):
        author = item['participants'][0]

        if author['type'] == 'commitee':
            return "%s Committee" % author['participant']
        else:
            return author['participant']

    def item_link(self, item):
        return 'http://openstates.sunlightlabs.com/api/v1/events/%s/' % (
            item['_id'])

    def item_pubdate(self, item):
        return item['when']
