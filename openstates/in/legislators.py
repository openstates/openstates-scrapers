import re
import difflib
import urlparse
import collections

import lxml.html

from billy.utils import metadata
from billy.scrape.legislators import LegislatorScraper, Legislator
import scrapelib

from .apiclient import ApiClient


class INLegislatorScraper(LegislatorScraper):
    jurisdiction = 'in'
    meta = metadata(jurisdiction)

    # The value to pass to the api as the "session" url component.
    api_session = '2013'

    def api_legislators(self):
        legislators = self.client.get('chamber_legislators',
            session=self.api_session, chamber=self.api_chamber)
        for data in legislators['items']:
            yield data
        while True:
            if 'nextLink' in legislators:
                legislators = self.client.get_relurl(legislators['nextLink'])
                for data in legislators['items']:
                    yield data
            else:
                break

    def scrape(self, chamber, term):
        self.retry_attempts = 0
        self.client = ApiClient(self)
        self.api_chamber = dict(upper='senate', lower='house')[chamber]

        districts = self.get_districts(chamber)
        for data in self.api_legislators():
            data = self.client.get_relurl(data['link'])
            name = '%s %s' % (data['firstName'], data['lastName'])

            matches = difflib.get_close_matches(name, districts)
            if not matches:
                msg = "Found no matching district for legislator %r." % data
                self.warning(msg)
                continue
            key = matches[0]
            district = districts[key]['district']
            leg_url = districts[key]['url']

            photo_url = data['pngDownloadLink']
            photo_url = urlparse.urljoin(self.client.root, photo_url)
            leg = Legislator(
                term, chamber, district, name,
                first_name=data['firstName'],
                last_name=data['lastName'],
                party=data['party'],
                photo_url=photo_url)

            url = self.client.make_url('chamber_legislators',
                session=self.api_session, chamber=self.api_chamber)
            leg.add_source(url)
            leg.add_source(leg_url)

            for comm in data['committees']:
                leg.add_role(
                    'member', term=term, chamber=chamber,
                    commmittee=comm['name'])

            self.save_legislator(leg)

    def get_districts(self, chamber):
        urls = {
            'upper': ('https://secure.in.gov/cgi-bin/legislative/listing/'
                      'listing-2.pl?data=district&chamber=Senate'),
            'lower': ('https://secure.in.gov/cgi-bin/legislative/listing/'
                      'listing-2.pl?data=district&chamber=House')}
        res = collections.defaultdict(dict)
        url = urls[chamber]
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        scrub = lambda el: el.text_content().strip()
        for tr in doc.xpath('//table/tr')[1:]:
            dist1, leg1, _, dist2, leg2 = tr

            dist1 = scrub(dist1)
            leg1_name = leg1.xpath('string(a)').strip()
            leg1_url = leg1.xpath('a/@href')[0]

            dist2 = scrub(dist2)
            leg2_name = leg2.xpath('string(a)').strip()
            leg2_url = leg2.xpath('a/@href')[0]

            res[leg1_name] = dict(district=dist1, url=leg1_url)
            res[leg2_name] = dict(district=dist2, url=leg2_url)
        return res
