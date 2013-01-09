import json
import datetime

from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import clean_committee_name

import lxml.html
import scrapelib

class NVLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nv'

    def scrape(self, chamber, term_name):

        for t in self.metadata['terms']:
            if t['name'] == term_name:
                session = t['sessions'][-1]
                slug = self.metadata['session_details'][session]['slug']

        if chamber == 'upper':
            chamber_slug = 'Senate'
        elif chamber == 'lower':
            chamber_slug = 'Assembly'

        leg_base_url = 'http://www.leg.state.nv.us/App/Legislator/A/%s/%s/' % (chamber_slug, slug)
        leg_json_url = 'http://www.leg.state.nv.us/App/Legislator/A/api/%s/Legislator?house=%s' % (slug, chamber_slug)

        resp = json.loads(self.urlopen(leg_json_url))

        for item in resp:
            leg = Legislator(term_name, chamber, item['DistrictNbr'],
                             item['FullName'], party=item['Party'],
                             photo_url=item['PhotoURL'])
            leg_url = leg_base_url + str(item['MemberID'])

            # fetch office from legislator page
            try:
                doc = lxml.html.fromstring(self.urlopen(leg_url))
                address = doc.xpath('//div[@class="contactAddress"]')[0].text_content()
                address2 = doc.xpath('//div[@class="contactAddress2"]')
                if address2:
                    address += ' ' + address2[0].text_content()
                address += '\n' + doc.xpath('//div[@class="contactCityStateZip"]')[0].text_content()
                phone = doc.xpath('//div[@class="contactPhone"]')[0].text_content()

                leg.add_office('district', 'District Address', address=address,
                               phone=phone)
            except scrapelib.HTTPError:
                self.warning('could not fetch %s' % leg_url)
                pass

            leg.add_source(leg_url)
            self.save_legislator(leg)
