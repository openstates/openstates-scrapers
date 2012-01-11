from collections import defaultdict
from urlparse import urlunsplit
from urllib import urlencode
from operator import methodcaller
import pdb


import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator



class DELegislatorScraper(LegislatorScraper):
    state = 'de'

    def scrape(self, chamber, term, text=methodcaller('text_content')):

        url = {
            'upper': 'http://legis.delaware.gov/legislature.nsf/sen?openview&nav=senate',
            'lower': 'http://legis.delaware.gov/legislature.nsf/Reps?openview&Count=75&nav=house&count=75',
            }[chamber]


        doc = lxml.html.fromstring(self.urlopen(url).decode('iso-8859-1'))
        doc.make_links_absolute(url)

        # Sneak into the main table...
        xpath = '//font[contains(., "Leadership Position")]/ancestor::table[1]'
        table = doc.xpath(xpath)[0]

        # Skip the first tr (headings)
        trs = table.xpath('tr')[1:]

        for tr in trs:

            bio_url = tr.xpath('descendant::a/@href')[0]
            name, _, district = map(text, tr.xpath("td"))

            leg = self.scrape_bio(term, chamber, district, name, bio_url)
            leg.add_source(url)
            self.save_legislator(leg)
            

    def scrape_bio(self, term, chamber, district, name, url):
        # this opens the committee section without having to do another request
        url += '&TableRow=1.5.5'
        doc = lxml.html.fromstring(self.urlopen(url))
        doc.make_links_absolute(url)

        # party is in one of these
        party = doc.xpath('//div[@align="center"]/b/font[@size="2"]/text()')
        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'

        leg = Legislator(term, chamber, district, name, party=party, url=url)

        photo_url = doc.xpath('//img[contains(@src, "FieldElemFormat")]/@src')
        if photo_url:
            leg['photo_url'] = photo_url[0]

        roles = defaultdict(lambda: {})
        
        position = 'member'            
        for text in doc.xpath('//td[@width="584"]/descendant::font/text()'):
            text = text.strip()
            if text == 'Committee Chair:':
                position = 'chair'
            elif text == 'Committee Co-chair:':
                position = 'co-chair'
            else:
                for committee in text.splitlines():
                    roles[committee].update(
                        role='committee member',
                        term=term,
                        chamber=chamber,
                        committee=committee,
                        party=party,
                        position=position)

        for role in roles.values():
            leg.add_role(**role)
            

        return leg
