from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

def normalize_name(name):
    """
        normalize names like DeMARCO, John and GOOSE, Ann for AL legislators
    """
    pieces = name.split(', ',)
    last = pieces[0]
    first = pieces[1]

    # handle suffixes either in the comma split or at end of first name
    if len(pieces) == 3:
        suffixes = pieces[2]
    else:
        suffixes = ''

    # move suffix off first name
    if first.endswith('Jr.') or first.endswith('Sr.'):
        suffixes = first[-3:]
        first = first[:-4]

    # lowercasing letters not preceeded by a lower case letter
    newlast = ''
    next_lower = False
    for letter in last:
        if next_lower:
            newlast += letter.lower()
        else:
            newlast += letter
        next_lower = not letter.islower()

    return first, newlast, suffixes



class ALLegislatorScraper(LegislatorScraper):
    state = 'al'

    def scrape(self, chamber, term):
        urls = {'upper': 'http://www.legislature.state.al.us/senate/senators/senateroster_alpha.html',
                'lower': 'http://www.legislature.state.al.us/house/representatives/houseroster_alpha.html'}
        party_dict = {'(D)': 'Democratic', '(R)': 'Republican'}

        url = urls[chamber]

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            for row in doc.xpath('//strong[starts-with(text(), "MEMBERS")]/following-sibling::table/tr')[1:]:
                name, party, district, office, phone = row.getchildren()

                # if the name column contains a link it isn't vacant
                link = name.xpath('a')
                if link:
                    name = name.text_content()
                    name = ' '.join(normalize_name(name))

                    party = party_dict[party.text_content()]
                    district = district.text_content().strip()
                    office = office.text_content().strip()
                    phone = phone.text_content().strip()
                    leg_url = link[0].get('href')

                    office_address = 'Room %s\n11 S. Union Street\nMontgomery, AL 36130' % office

                    leg = Legislator(term, chamber, district, name,
                                     party=party, office_phone=phone,
                                     office_address=office_address,
                                     url=leg_url)
                    self.get_details(leg, term, leg_url)

                    leg.add_source(url)
                    self.save_legislator(leg)

    def get_details(self, leg, term, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        photo = doc.xpath('//img[@height="250"]/@src')
        if photo:
            leg['photo_url'] = photo[0]
        for com in doc.xpath('//ul/li'):
            com = com.text_content()
            if '(' in com:
                com, position = com.split('(')
                com = com.strip()
                position = position.replace(')', '').lower().strip()
            else:
                position = 'member'
            leg.add_role('committee member', term=leg['roles'][0]['term'],
                         chamber=leg['roles'][0]['chamber'], committee=com,
                         position=position)
        leg.add_source(url)
