import csv
from collections import defaultdict
from cStringIO import StringIO

from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod

import lxml.html

class MNLegislatorScraper(LegislatorScraper):
    jurisdiction = 'mn'
    latest_only = True

    _parties = {'DFL': 'Democratic-Farmer-Labor',
                'R': 'Republican'}

    def scrape(self, chamber, term):
        if chamber == 'lower':
            self.scrape_house(term)
        else:
            self.scrape_senate(term)

    def scrape_house(self, term):
        url = 'http://www.house.leg.state.mn.us/members/housemembers.asp'

        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        # skip first header row
        for row in doc.xpath('//tr')[1:]:
            tds = [td.text_content().strip() for td in row.xpath('td')]
            if len(tds) == 5:
                district = tds[0].lstrip('0')
                name, party = tds[1].rsplit(' ', 1)
                if party == '(R)':
                    party = 'Republican'
                elif party == '(DFL)':
                    party = 'Democratic-Farmer-Labor'
                leg_url = row.xpath('td[2]/p/a/@href')[0]
                addr = tds[2]
                phone = tds[3]
                email = tds[4]

            leg = Legislator(term, 'lower', district, name,
                             party=party, email=email, url=leg_url)

            addr = ('{0} State Office Building\n'
                    '100 Rev. Dr. Martin Luther King Jr. Blvd.\n'
                    'St. Paul, MN 55155').format(addr)
            leg.add_office('capitol', 'Capitol Office', address=addr,
                           phone=phone)

            # add photo_url
            leg_html = self.urlopen(leg_url)
            leg_doc = lxml.html.fromstring(leg_html)
            img_src = leg_doc.xpath('//img[contains(@src, "memberimg")]/@src')
            if img_src:
                leg['photo_url'] = img_src[0]

            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)

    def scrape_senate(self, term):

        index_url = 'http://www.senate.mn/members/index.php'
        doc = lxml.html.fromstring(self.urlopen(index_url))
        doc.make_links_absolute(index_url)

        leg_data = defaultdict(dict)

        # get all the tds in a certain div
        tds = doc.xpath('//div[@id="hide_show_alpha_all"]//td[@style="vertical-align:top;"]')
        for td in tds:
            # each td has 2 <a>s- site & email
            main_link, email = td.xpath('.//a')
            # get name
            name = main_link.text_content().split(' (')[0]
            leg = leg_data[name]
            leg['leg_url'] = main_link.get('href')
            leg['photo_url'] = td.xpath('./preceding-sibling::td/a/img/@src')[0]
            if 'mailto:' in email.get('href'):
                leg['email'] = email.get('href').replace('mailto:', '')

        self.info('collected preliminary data on %s legislators', len(leg_data))
        assert leg_data

        # use CSV for most of data
        csv_url = 'http://www.senate.mn/members/member_list_ascii.php?ls='
        csvfile = self.urlopen(csv_url)

        for row in csv.DictReader(StringIO(csvfile)):
            if not row['First Name']:
                continue
            name = '%s %s' % (row['First Name'], row['Last Name'])
            party = self._parties[row['Party']]
            leg = Legislator(term, 'upper', row['District'].lstrip('0'), name,
                             party=party,
                             first_name=row['First Name'],
                             last_name=row['Last Name'],
                             **leg_data[name]
                            )

            row['Rm Number'] = row['Rm. Number']  # .format issue with "."
            leg.add_office('capitol', 'Capitol Office',
                           address='{Office Building}\n{Office Address}\nRoom {Rm Number}\n{City}, {State} {Zipcode}'.format(**row)
                           )


            leg.add_source(csv_url)
            leg.add_source(index_url)

            self.save_legislator(leg)
