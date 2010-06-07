from __future__ import with_statement
import urlparse
import datetime as dt

from fiftystates.scrape.oh import metadata
from fiftystates.scrape.oh.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill

import xlrd
import urllib


class OHBillScraper(BillScraper):
	state = 'oh'


	def scrape(self, chamber, year):
		if int(year) < 2009 or int(year) > dt.date.today().year:
			raise NoDataForYear(year)

		if chamber == 'upper':
			self.scrape_house_bills()
		else:
			self.scrape_senate_bills()


	def scrape_house_bills(self):

		# Will try later when ready to read from online
		house_bills_url = 'http://www.lsc.state.oh.us/status128/hb.xls'
		house_bills_file = urllib.urlopen(house_bills_url).read()
		f = open('oh_bills.xls','w')
		f.write(house_bills_file)
		f.close()
		
		
		wb = xlrd.open_workbook('oh_bills.xls')
		sh = wb.sheet_by_index(0)


		for rownum in range(1, sh.nrows):
			
			bill_id = int(rownum)
			bill_title = str(sh.cell(rownum, 3).value) 
			bill = Bill( '128', 'upper', bill_id, bill_title)
			bill.add_sponsor( 'primary', str(sh.cell(rownum, 1).value) )

			if sh.cell(rownum, 2).value is not '':
				bill.add_sponsor( 'cosponsor', str(sh.cell(rownum, 2).value) )

			actor = ""

			#Actions - starts column after bill title
			for colnum in range( 4, sh.ncols - 1):
			
	
				coltitle = str(sh.cell(0, colnum).value)
				cell = sh.cell(rownum, colnum)				

				if len(coltitle) != 0:

					if coltitle.split()[0] == 'House':
						actor = "upper"
					elif coltitle.split()[0] == 'Senate':
						actor = "lower"
					elif coltitle.split()[-1] == 'Governor':
						actor = "Governor"
					else:
						actor = actor
 
				action = str(sh.cell( 0, colnum).value)
				date = cell.value

				if type(cell.value) == float:
					bill.add_action(actor, action, date) 	

				if (len(coltitle) != 0 ) and coltitle.split()[-1] == 'Committee':
					committee = str(cell.value)
					bill.add_action(committee, action, date = '')

			self.save_bill(bill)
