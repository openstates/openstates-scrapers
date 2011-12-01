from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html


class DELegislatorScraper(LegislatorScraper):
    state = 'de'

    def scrape(self, chamber, term):
        chamber_name = {'upper': 'senate', 'lower': 'house'}[chamber]
        url = 'http://legis.delaware.gov/legislature.nsf/Reps?openview&Count=75&nav=%s&count=75' % (chamber_name)

        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for row in page.xpath('//table/tr/td[@width="96%"]/table/tr[@valign="top"]'):
            name = row.xpath('td/font/a')[0].text
            district = row.xpath('td[@align="center"]/font')[0].text
            bio_page = row.xpath('td/font/a')[0].attrib['href']

            leg = self.scrape_bio(term, chamber, district, name, bio_page)

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

        #position = 'member'
        #for child in doc.xpath('//td[@width="584"]'):
        #    text = child.text_content().strip()
        #    if text == 'Committee Chair:':
        #        position = 'chair'
        #    elif text == 'Committee Co-chair:':
        #        position = 'co-chair'
        #    else:
        #        for com in text.splitlines():
        #            leg.add_role('committee member', term=term,
        #                         chamber=chamber, committee=com,
        #                         position=position)

        return leg
