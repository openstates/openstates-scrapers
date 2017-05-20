import re
import lxml.html
from pupa.scrape import Person, Scraper
from openstates.utils import LXMLMixin


class AKPersonScraper(Scraper, LXMLMixin):
    jurisdiction = 'ak'
    latest_only = True

    def _scrape_offices(self, leg, url, email):
        doc = self.lxmlize(url)

        capitol_office = doc.xpath('//strong[text()="Session Contact"]')[0].getparent().text_content().strip().splitlines()
        capitol_office = [line.strip() for line in capitol_office]

        assert capitol_office[0] == 'Session Contact'
        assert capitol_office[3].startswith('Phone:')
        assert capitol_office[4].startswith('Fax:')

        leg.add_contact_detail(
            type = 'address',
            value = capitol_office[1] + '\n' + capitol_office[2],
            note = 'Capitol Office',
        )
        
        
        if len(capitol_office[3]) > len('Phone:'):
            leg.add_contact_detail(
                type='voice', 
                value=capitol_office[3][len('Phone: '): ],
                note='Capitol Office Phone',
            )
        
        if len(capitol_office[4]) > len('Fax:'):
            leg.add_contact_detail(
                type='fax', 
                value=capitol_office[4][len('Fax: '): ],
                note='Capitol Office Fax',
            )
        
        leg.add_contact_detail(
            type='email', 
            value=email,
            note='E-mail',
        )
        
        interim_office = doc.xpath('//strong[text()="Interim Contact"]')
        if interim_office:
            interim_office = interim_office[0].getparent().text_content().strip().splitlines()
            interim_office = [line.strip() for line in interim_office]
            assert interim_office[0] == 'Interim Contact'
            assert interim_office[3].startswith('Phone:')
            assert interim_office[4].startswith('Fax:')


            leg.add_contact_detail(
                type = 'address',
                note = 'District Office',
                value = interim_office[1] + '\n' + interim_office[2],
            
            )
        
            if len(interim_office[3]) > len('Phone:'):
                leg.add_contact_detail(
                    type='voice', 
                    value=interim_office[3][len('Phone: '): ],
                    note='District Office Phone',
                )
        
            if len(interim_office[4]) > len('Fax:'):
                leg.add_contact_detail(
                    type='fax', 
                    value=interim_office[4][len('Fax: '): ],
                    note='District Office Fax',
                )
            


    def scrape_chamber(self, chamber):
        self._party_map = {
            'Democrat': 'Democratic',
            'Republican': 'Republican',
            'Non Affiliated': 'Independent',
            'Not Affiliated': 'Independent',
        }

        if chamber == 'upper':
            url = 'http://senate.legis.state.ak.us/'
        else:
            url = 'http://house.legis.state.ak.us/'

        page = self.lxmlize(url)

        items = page.xpath('//ul[@class="item"]')[1].getchildren()

        for item in items:
            photo_url = item.xpath('.//img/@src')[0]
            name = item.xpath('.//strong/text()')[0]
            leg_url = item.xpath('.//a/@href')[0]
            email = item.xpath('.//a[text()="Email Me"]/@href')
            if email:
                email = email[0].replace('mailto:', '')
            else:
                self.warning('no email for ' + name)

            party = district = phone = fax = None
            skip = False

            for dt in item.xpath('.//dt'):
                dd = dt.xpath('following-sibling::dd')[0].text_content()
                label = dt.text.strip()
                if label == 'Party:':
                    party = dd
                elif label == 'District:':
                    district = dd
                elif label == 'Phone:':
                    phone = dd
                elif label == 'Fax:':
                    fax = dd
                elif label.startswith('Deceased'):
                    skip = True
                    self.warning('skipping deceased ' + name)
                    break

            if skip:
                continue

            person = Person(
                district=district,
                name=name,
                party=self._party_map[party],
                image=photo_url,
                #email=email,
                #url=leg_url,
            )
            person.add_source(leg_url)
            person.add_link(leg_url)

            # scrape offices
            self._scrape_offices(person, leg_url, email)

            yield person
            
            
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')
