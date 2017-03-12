import re

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

import xlrd

excel_mapping = {
    'district': 0,
    'town_represented': 1,
    'full_name': 2,
    'party': 3,
    'address': 4,
    'email': 5,
}

translate = {
    "Democrat": "Democratic",
    "Republican": "Republican",
    "Independent": "Independent"
}

link_col_ix = 4


class RILegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ri'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            url = ('http://webserver.rilin.state.ri.us/Documents/Senators.xls')
            rep_type = 'Senator'
            contact_url = 'http://webserver.rilin.state.ri.us/Email/SenEmailListDistrict.asp'
        elif chamber == 'lower':
            url = ('http://webserver.rilin.state.ri.us/Documents/Representatives.xls')
            rep_type = 'Representative'
            contact_url = 'http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp'

        contact_page = self.lxmlize(contact_url)
        contact_info_by_district = {}
        for row in contact_page.xpath('//tr[@valign="TOP"]'):
            tds = row.xpath('td')
            (detail_link, ) = tds[link_col_ix].xpath('.//a/@href')
            # Ignore name (2nd col). We have a regex built up below for the spreadsheet name I don't want to touch
            district, _, email, phone = [td.text_content().strip() for td in tds[:link_col_ix]]
            contact_info_by_district[district] = {
                'email': email,
                'phone': phone,
                'detail_link': detail_link,
            }

        self.urlretrieve(url, 'ri_leg.xls')

        wb = xlrd.open_workbook('ri_leg.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(1, sh.nrows):
            d = {
                field: sh.cell(rownum, col_num).value
                for field, col_num in excel_mapping.iteritems()
            }

            # Convert float to an int, and then to string, the format required by billy
            district = str(int(d['district']))
            if d['full_name'].upper() == "VACANT":
                self.warning(
                    "District {}'s seat is vacant".format(district))
                continue

            contact_info = contact_info_by_district[district]

            # RI is very fond of First M. Last name formats and
            # they're being misparsed upstream, so fix here
            (first, middle, last) = ('', '', '')
            full_name = re.sub(r"^{}(?=\s?[A-Z].*$)".format(rep_type), '', d['full_name']).strip()
            if re.match(r'^\S+\s[A-Z]\.\s\S+$', full_name):
                (first, middle, last) = full_name.split()

            # Note - if we ever need to speed this up, it looks like photo_url can be mapped from the detail_link a la
            # /senators/Paolino/ -> /senators/pictures/Paolino.jpg
            detail_page = self.lxmlize(contact_info['detail_link'])
            (photo_url, ) = detail_page.xpath('//div[@class="ms-WPBody"]//img/@src')

            leg = Legislator(
                term, chamber, district, full_name,
                first, last, middle, translate[d['party']],
                photo_url=photo_url,
                town_represented=d['town_represented'],
                url=detail_link,
            )

            leg.add_office(
                'district',
                'District Office',
                address=d['address'],
                phone=contact_info['phone'],
                email=contact_info['email']
            )
            leg.add_source(contact_url)
            leg.add_source(contact_info['detail_link'])
            self.save_legislator(leg)
