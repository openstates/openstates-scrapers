import re
import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator

class SCLegislatorScraper(LegislatorScraper):
    state = 'sc'

    def scrape(self, chamber, term):
        if chamber == 'lower':
            url = 'http://www.scstatehouse.gov/html-pages/housemembers.html'
        else:
            url = 'http://www.scstatehouse.gov/html-pages/senatemembersd.html'

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            rows = doc.xpath('//pre/div[@class="sansSerifNormal"]')

            for row in rows[1:]:
                member_a = row.xpath('a')[0]

                name_party = member_a.text_content()
                if name_party.find('[D]') != -1:
                    party = 'Democratic'
                    full_name = name_party.partition('[D]')[0].strip()
                elif name_party.find('[R]') != -1:
                    party = 'Republican'
                    full_name = name_party.partition('[R]')[0].strip()

                photo_url = 'http://www.scstatehouse.gov/members/gif/' + re.search('(\d+)\.html', member_a.attrib['href']).group(1) + '.jpg'

                other_data = row.text_content().encode('ascii', 'ignore')
                od_result = re.search('^.+District (\d+) - (.+)Count.+$', other_data)
                district = od_result.group(1)

                contentb = re.search('^.+\(C\) (.+,.*\d+).*Bus. (\(\d+\) \d+-\d+).+$', other_data)
                if contentb is not None:
                    office_address = contentb.group(1)
                    office_phone = contentb.group(2)

                legislator = Legislator(term, chamber, district, full_name, party=party, photo_url=photo_url, office_address=office_address, office_phone=office_phone)
                legislator.add_source(url)
                self.save_legislator(legislator)
