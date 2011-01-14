from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

def get_surrounding_block(doc, key):
    value = doc.xpath('//*[contains(text(), "%s")]/..' % key)[0]
    return value.text_content()


class DCLegislatorScraper(LegislatorScraper):
    state = 'dc'

    def scrape(self, chamber, term):
        # this beautiful page is loaded from the council page via AJAX
        url = 'http://www.dccouncil.washington.dc.us/include/linkedpage.aspx?linkedpage=2&page=17'

        # do nothing if they're trying to get a lower chamber
        if chamber == 'lower':
            return

        with self.urlopen(url) as data:
            base_doc = lxml.html.fromstring(data)

            for link in base_doc.xpath('//a'):
                leg_url = 'http://www.dccouncil.washington.dc.us/' + link.get('href')
                with self.urlopen(leg_url) as leg_html:
                    doc = lxml.html.fromstring(leg_html)
                    name = link.text

                    # Name, District
                    title = doc.get_element_by_id('PageTitle')
                    district = title.text.rsplit(', ')[-1]

                    # party
                    party = get_surrounding_block(doc, 'Political Affiliation')
                    if 'Democratic' in party:
                        party = 'Democratic'
                    else:
                        party = 'Independent'

                    legislator = Legislator(term, 'upper', district, name,
                                            party=party)
                    legislator.add_source(leg_url)
                self.save_legislator(legislator)
