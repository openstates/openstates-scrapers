from fiftystates.scrape.legislators import LegislatorScraper, Legislator

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

        url = urls[chamber]

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for row in doc.xpath('//strong[starts-with(text(), "MEMBERS")]/following-sibling::table/tr')[1:]:
                name, party, district, office, phone = row.getchildren()

                # if the name column contains a link it isn't vacant
                link = name.xpath('a')
                if link:
                    name = name.text_content()
                    name = ' '.join(normalize_name(name))

                    party = party.text_content()
                    district = district.text_content()
                    office = office.text_content()
                    phone = phone.text_content()

                    leg = Legislator(term, chamber, district, name, party,
                                     phone=phone, office=office,
                                     url=link[0].get('href'))
                    leg.add_source(url)
                    self.save_legislator(leg)
