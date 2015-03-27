import csv
from collections import defaultdict
from cStringIO import StringIO

from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod

import lxml.html
import xlrd

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
        URL = 'http://www.house.leg.state.mn.us/members/meminfo.xls'
        xls, _ = self.urlretrieve(URL)
        wb = xlrd.open_workbook(xls)
        sh = wb.sheet_by_index(0)

        headers = [x.value for x in sh.row(0)]
        assert headers == [
                'district_id', 'party',
                'first name', 'last name', 'longname',
                'SOB_room', 'SOB_city_state_ZIP', 'SOB_office_phone',
                'perfered_interim_mailing_address', 'perfered__interimmailing_city', 'state', 'perfered__interim_mailing_zip',
                'emailalias'
                ]

        for row_num in range(1, sh.nrows):
            leg = Legislator(
                    term=term,
                    chamber='lower',
                    district=sh.cell_value(row_num, 0).lstrip("0"),
                    full_name=sh.cell_value(row_num, 4)[len("Rep. "): ],
                    party=self._parties[sh.cell_value(row_num, 1)]
                    )
            leg.add_source(URL)

            leg.add_office(
                    type='capitol',
                    name="Capitol Office",
                    address="{0}\n{1}".format(sh.cell_value(row_num, 5), sh.cell_value(row_num, 6)),
                    phone=sh.cell_value(row_num, 7),
                    email=sh.cell_value(row_num, 12) + "@house.mn"
                    )
            if sh.cell_value(row_num, 5) != sh.cell_value(row_num, 8):
                assert sh.cell_value(row_num, 10) == "Minnesota"
                leg.add_office(
                        type='district',
                        name="District Office",
                        address="{0}\n{1}, MN {2}".format(sh.cell_value(row_num, 8), sh.cell_value(row_num, 9), sh.cell_value(row_num, 11))
                        )

            self.save_legislator(leg)

    def scrape_senate(self, term):
        index_url = 'http://www.senate.mn/members/index.php'
        doc = lxml.html.fromstring(self.get(index_url).text)
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
        csvfile = self.get(csv_url).text

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
