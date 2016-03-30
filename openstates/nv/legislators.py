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

        resp = json.loads(self.get(leg_json_url).text)

        for item in resp:
            # empty district
            empty_names = ['District No', 'Vacant']
            if any(name in item['FullName'] for name in empty_names):
                continue
            last, first = item['FullName'].split(",", 1)
            item['FullName'] = "{first} {last}".format(last=last,
                                                       first=first).strip()
            leg = Legislator(term_name, chamber, item['DistrictNbr'],
                             item['FullName'], party=item['Party'],
                             photo_url=item['PhotoURL'])
            leg_url = leg_base_url + item['DistrictNbr']

            # hack to get the legislator ID
            html = self.get(leg_url).text
            for l in html.split('\n'):
                if 'GetLegislatorDetails' in l:
                    leg_id = l.split(',')[1].split("'")[1]

            # fetch the json used by the page
            leg_details_url = 'https://www.leg.state.nv.us/App/Legislator/A/api/78th2015/Legislator?id=' + leg_id
            leg_resp = json.loads(self.get(leg_details_url).text)
            details = leg_resp['legislatorDetails']

            address = details['Address1']
            address2 = details['Address2']
            if address2:
                address += ' ' + address2
            address += '\n%s, NV %s' % (details['City'], details['Zip'])

            phone = details['LCBPhone']
            email = details['LCBEmail']

            leg.add_office('district', 'District Address', address=address,
                                   phone=phone,email=email)
            leg.add_source(leg_details_url)
            self.save_legislator(leg)
