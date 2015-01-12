from billy.scrape.legislators import LegislatorScraper, Legislator

from . import ksapi
import json


class KSLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ks'

    def scrape(self, term, chambers):
        content = json.loads(self.urlopen(ksapi.url + 'members/'))['content']
        if 'upper' in chambers:
            for member in content['senate_members']:
                self.get_member(term, 'upper', member['KPID'])
        if 'lower' in chambers:
            for member in content['house_members']:
                self.get_member(term, 'lower', member['KPID'])


    def get_member(self, term, chamber, kpid):
        url = '%smembers/%s' % (ksapi.url, kpid)
        content = json.loads(self.urlopen(url))['content']

        party = content['PARTY']
        if party == 'Democrat':
            party = 'Democratic'

        slug = {'2013-2014': 'b2013_14',
                '2015-2016': 'b2015_16'}[term]
        leg_url = 'http://www.kslegislature.org/li/%s/members/%s/' % (slug, kpid)
        photo_url = 'http://www.kslegislature.org/li/m/images/pics/%s.jpg' % kpid
        #photo = legislator_page.xpath('//img[@class="profile-picture"]/@src')[0]

        legislator = Legislator(term, chamber, str(content['DISTRICT']),
                                content['FULLNAME'], email=content['EMAIL'],
                                party=party, url=leg_url, photo_url=photo_url,
                                occupation=content['OCCUPATION'],
                               )

        # just do office address for now, can get others from api
        # if content['OFFICENUM']:
        #     address = ('Kansas House of Representatives\n'
        #                'Docking State Office Building\n'
        #                '901 SW Harrison Street\n'
        #                'Topeka, KS 66612')
        # else:

        address = ('Room %s\n'
                   'Kansas State Capitol Building\n'
                   '300 SW 10th St.\n'
                   'Topeka, KS 66612') % content['OFFICENUM']

        legislator.add_office('capitol', 'Capitol Office',
                              phone=content['OFFPH'] or None,
                              address=address)

        legislator.add_source(url)
        self.save_legislator(legislator)
