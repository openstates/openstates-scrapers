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

  def scrape(self, chamber, term):
    self.validate_term(term, latest_only=True)

    if chamber == 'upper':
      url = ('http://www.rilin.state.ri.us/Documents/Senators.xls')
      rep_type = 'Senator '
    elif chamber == 'lower':
      url = ('http://www.rilin.state.ri.us/Documents/Representatives.xls')
      rep_type = 'Representative '

    with self.urlopen(url) as senator_xls:
      with open('ri_senate.xls', 'w') as f:
        f.write(senator_xls)

    wb = xlrd.open_workbook('ri_senate.xls')
    sh = wb.sheet_by_index(0)

    for rownum in xrange(1, sh.nrows):
      d = {}
      for field, col_num in excel_mapping.iteritems():
        d[field] = str(sh.cell(rownum, col_num).value)
      district_name = "District " + d['district']
      full_name = re.sub(rep_type, '', d['full_name']).strip()
      leg = Legislator(term, chamber, district_name, full_name,
                       '', '', '',
                       d['party'], 
                       office_address=d['address'],
                       town_represented=d['town_represented'],
                       email=d['email'])
      leg.add_source(url)

      self.save_legislator(leg)

