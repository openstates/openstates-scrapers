import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd

_party_map = {'D': 'Democrat', 'R':'Republican', 'U':'Independent'}

class RILegislatorScraper(LegislatorScraper):
  state = 'ri'

  def scrape(self, chamber, term):
      self.validate_term(term, latest_only=True)

      if chamber == 'upper':
          self.scrape_senators(chamber, term)
      # elif chamber == 'lower':
      #     self.scrape_reps(chamber, term)

  def scrape_senators(self, chamber, term_name):
    url = ('http://www.rilin.state.ri.us/Documents/Senators.xls')

    mapping = {
        'district': 0,
        'town_represented': 2,        
        'full_name': 3,
        'party': 4,
        'address': 5,
        'email': 6,
    }


    with self.urlopen(url) as senator_xls:
      with open('me_senate.xls', 'w') as f:
        f.write(senator_xls)

    wb = xlrd.open_workbook('me_senate.xls')
    sh = wb.sheet_by_index(0)

    for rownum in xrange(1, sh.nrows):
      d = {}
      for field, col_num in mapping.iteritems():
        d[field] = str(sh.cell(rownum, col_num).value)
        self.log(d)
        
        