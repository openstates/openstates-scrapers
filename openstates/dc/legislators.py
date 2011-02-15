from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

def get_surrounding_block(doc, key):
    value = doc.xpath('//*[contains(text(), "%s")]/..' % key)[0]
    return value.text_content()


class DCLegislatorScraper(LegislatorScraper):
    state = 'dc'

    def scrape(self, chamber, term):
        urls = ['http://www.dccouncil.washington.dc.us/chairman',
                'http://www.dccouncil.washington.dc.us/chairprotempore',
                'http://www.dccouncil.washington.dc.us/at-largemembers',
                'http://www.dccouncil.washington.dc.us/wardmembers']

        # do nothing if they're trying to get a lower chamber
        if chamber == 'lower':
            return

        for url in urls:

            with self.urlopen(url) as data:
                doc = lxml.html.fromstring(data)

                for link in doc.xpath('//div[@style="padding-right: 5px;"]/a'):
                    leg_url = ('http://www.dccouncil.washington.dc.us/' +
                               link.get('href'))
                    with self.urlopen(leg_url) as leg_html:
                        ldoc = lxml.html.fromstring(leg_html)
                        name = link.text

                        # Name, District
                        title = ldoc.get_element_by_id('PageTitle')
                        district = title.text.rsplit(', ')[-1]

                        # party
                        party = get_surrounding_block(ldoc,
                                                      'Political Affiliation')
                        if 'Democratic' in party:
                            party = 'Democratic'
                        else:
                            party = 'Independent'

                        legislator = Legislator(term, 'upper', district, name,
                                                party=party)
                        legislator.add_source(leg_url)
                    self.save_legislator(legislator)
