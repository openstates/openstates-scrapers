from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

from . import ksapi
import json
import scrapelib


class KSLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ks'

    def scrape(self, term, chambers):
        content = json.loads(self.get(ksapi.url + 'members/').text)['content']
        if 'upper' in chambers:
            for member in content['senate_members']:
                self.get_member(term, 'upper', member['KPID'])
        if 'lower' in chambers:
            for member in content['house_members']:
                self.get_member(term, 'lower', member['KPID'])


    def get_member(self, term, chamber, kpid):
        url = '%smembers/%s' % (ksapi.url, kpid)
        content = json.loads(self.get(url).text)['content']

        party = content['PARTY']
        if party == 'Democrat':
            party = 'Democratic'

        slug = {'2013-2014': 'b2013_14',
                '2015-2016': 'b2015_16'}[term]
        leg_url = 'http://www.kslegislature.org/li/%s/members/%s/' % (slug, kpid)

        try:
            legislator_page = self.lxmlize(leg_url)
            (photo_url, ) = legislator_page.xpath(
                    '//img[@class="profile-picture"]/@src')
        except scrapelib.HTTPError:
            self.warning("{}'s legislator bio page not found".format(content['FULLNAME']))
            leg_url = ''
            photo_url = ''

        legislator = Legislator(term, chamber, str(content['DISTRICT']),
                                content['FULLNAME'],
                                party=party, url=leg_url, photo_url=photo_url,
                                occupation=content['OCCUPATION'],
                               )

        address = ('Room %s\n'
                   'Kansas State Capitol Building\n'
                   '300 SW 10th St.\n'
                   'Topeka, KS 66612') % content['OFFICENUM']

        legislator.add_office('capitol', 'Capitol Office',
                              phone=content['OFFPH'] or None,
                              address=address,
                              email=content['EMAIL'])

        legislator.add_source(url)
        self.save_legislator(legislator)
