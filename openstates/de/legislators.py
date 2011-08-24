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
            # TODO: scrape bio page for party affiliation
            bio_page = row.xpath('td/font/a')[0].attrib['href']
            district = row.xpath('td[@align="center"]/font')[0].text

            l = Legislator(term, chamber, district, name)
            l.add_source(url)

            self.save_legislator(l)
