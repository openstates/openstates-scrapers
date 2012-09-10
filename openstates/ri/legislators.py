import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd

excel_mapping = {
    'district': 0,
    'town_represented': 2,
    'full_name': 3,
    'party': 4,
    'address': 5,
    'email': 6,
}

class RILegislatorScraper(LegislatorScraper):
    state = 'ri'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            url = ('http://webserver.rilin.state.ri.us/Documents/Senators.xls')
            rep_type = 'Senator '
        elif chamber == 'lower':
            url = (
             'http://webserver.rilin.state.ri.us/Documents/Representatives.xls')
            rep_type = 'Representative '

        self.urlretrieve(url, 'ri_leg.xls')

        wb = xlrd.open_workbook('ri_leg.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(1, sh.nrows):
            d = {}
            for field, col_num in excel_mapping.iteritems():
                d[field] = sh.cell(rownum, col_num).value
            dist = str(int(d['district']))
            district_name = dist
            full_name = re.sub(rep_type, '', d['full_name']).strip()
            translate = {
                "Democrat"    : "Democratic",
                "Republican"  : "Republican",
                "Independent" : "Independent"
            }
            leg = Legislator(term, chamber, district_name, full_name,
                             '', '', '',
                             translate[d['party']],
                             town_represented=d['town_represented'],
                             email=d['email'])
            leg.add_office('district', 'Address', address=d['address'])
            leg.add_source(url)
            self.save_legislator(leg)

