import re
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

class ALLegislatorScraper(LegislatorScraper):
    jurisdiction = 'al'

    def scrape(self, chamber, term):
        urls = {'upper': 'http://www.legislature.state.al.us/senate/senators/senateroster_alpha.html',
                'lower': 'http://www.legislature.state.al.us/house/representatives/houseroster_alpha.html'}
        party_dict = {'(D)': 'Democratic', '(R)': 'Republican', 
                      '(I)': 'Independent'}

        url = urls[chamber]

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            for row in doc.xpath('//strong[starts-with(text(), "MEMBERS")]/following-sibling::table/tr')[1:]:
                name, party, district, office, phone = row.getchildren()

                # if the name column contains a link it isn't vacant
                link = name.xpath('a')
                if link:
                    name = name.text_content().strip()

                    party = party_dict[party.text_content().strip()]
                    district = district.text_content().strip()
                    office = office.text_content().strip()
                    phone = phone.text_content().strip()
                    leg_url = link[0].get('href')

                    office_address = 'Room %s\n11 S. Union Street\nMontgomery, AL 36130' % office

                    leg = Legislator(term, chamber, district, name,
                                     party=party, url=leg_url)
                    self.get_details(leg, term, leg_url)
                    leg.add_office('capitol', 'Capitol Office',
                                   address=office_address, phone=phone)

                    leg.add_source(url)
                    self.save_legislator(leg)

    def get_details(self, leg, term, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        photo = doc.xpath('//img[@height="250"]/@src')
        if photo:
            leg['photo_url'] = photo[0]
        email = doc.xpath('//a[starts-with(@href, "mailto")]/@href')
        if email:
            leg['email'] = email[0].strip('mailto:')
        for com in doc.xpath('//ul/li'):
            com = com.text_content()
            if '(' in com:
                com, position = com.split('(')
                position = position.replace(')', '').lower().strip()
            else:
                position = 'member'
            com = com.strip()
            com = com.replace(" No.","")
            leg.add_role('committee member', term=leg['roles'][0]['term'],
                         chamber=leg['roles'][0]['chamber'], committee=com,
                         position=position)
        leg.add_source(url)
