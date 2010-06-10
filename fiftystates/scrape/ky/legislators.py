import re
from BeautifulSoup import BeautifulSoup

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import Legislator, LegislatorScraper

def split_name(full_name):
    last_name = full_name.split(',')[0]
    rest = ','.join(full_name.split(',')[1:])

    m = re.search('(\w+)\s([A-Z])\.$', rest)
    if m:
        first_name = m.group(1)
        middle_name = m.group(2)
    else:
        first_name = rest
        middle_name = ''

    if last_name.endswith(' Jr.'):
        first_name += ' Jr.'
        last_name = last_name.replace(' Jr.', '')

    return (first_name.strip(), last_name.strip(), middle_name.strip())

class KYLegislatorScraper(LegislatorScraper):
    state = 'ky'

    def scrape(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            leg_list_url = 'http://www.lrc.ky.gov/senate/senmembers.htm'
        else:
            leg_list_url = 'http://www.lrc.ky.gov/house/hsemembers.htm'

        with self.urlopen(leg_list_url) as leg_list:
            leg_list = BeautifulSoup(leg_list)
            leg_table = leg_list.find(id="table2")

            for row in leg_table.findAll('tr')[1:]:
                leg_link = row.findAll('td')[1].font
                if leg_link: leg_link = leg_link.a
                if not leg_link:
                    # Vacant seat
                    continue

                full_name = leg_link.contents[0].strip()

                district = ""
                for text in row.findAll('td')[2].findAll(text=True):
                    district += text.strip()
                district = district.strip()

                self.parse_legislator(chamber, year, full_name,
                                      district, leg_link['href'])

    def parse_legislator(self, chamber, year, full_name, district, url):
        with self.urlopen(url) as leg_page:
            leg_page = BeautifulSoup(leg_page)
            name_str = leg_page.find('strong').contents[0].strip()

            if name_str.endswith('(D)'):
                party = 'Democrat'
            elif name_str.endswith('(R)'):
                party = 'Republican'
            elif name_str.endswith('(I)'):
                party = 'Independent'
            else:
                party = 'Other'

            full_name = full_name.replace('\n', '').replace('&quot;', '"')
            full_name = full_name.replace('\t', '').replace('\r', '')
            (first_name, last_name, middle_name) = split_name(full_name)

            legislator = Legislator(year, chamber, district, full_name,
                                    first_name, last_name, middle_name, party)
            legislator.add_source(url)

            self.save_legislator(legislator)
