from __future__ import with_statement
import urlparse
import datetime as dt

from fiftystates.scrape.oh import metadata
from fiftystates.scrape.oh.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill

import xlrd
import urllib
import lxml.etree


class OHBillScraper(BillScraper):
	state = 'oh'


	def scrape(self, chamber, year):
		if int(year) < 2009 or int(year) > dt.date.today().year:
			raise NoDataForYear(year)

		if chamber == 'upper':
			self.scrape_house_bills()
		elif chamber == 'lower':
			self.scrape_senate_bills()


	def scrape_house_bills(self):

		house_bills_url = 'http://www.lsc.state.oh.us/status128/hb.xls'
		house_jointres_url = 'http://www.lsc.state.oh.us/status128/hjr.xls'
		house_concurres_url = 'http://www.lsc.state.oh.us/status128/hcr.xls'
		files = (house_bills_url, house_jointres_url, house_concurres_url)

		for house_file in files:

			house_bills_file = urllib.urlopen(house_file).read()
			f = open('oh_bills.xls','w')
			f.write(house_bills_file)
			f.close()
		
		
			wb = xlrd.open_workbook('oh_bills.xls')
			sh = wb.sheet_by_index(0)
		
			house_file = str(house_file)
			if len(str(house_file)) == 44:
				file_type = house_file[len(house_file) - 7:len(house_file)-4]
			else:
				file_type = house_file[len(house_file) - 6:len(house_file)-4]

			for rownum in range(1, sh.nrows):
			
				bill_id = file_type + str(int(rownum))
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

				bill.add_source(house_file)
				self.scrape_votes(bill, file_type, rownum)

				self.save_bill(bill)



	def scrape_senate_bills(self):

		senate_bills_url = 'http://www.lsc.state.oh.us/status128/sb.xls'
		senate_jointres_url = 'http://www.lsc.state.oh.us/status128/sjr.xls'
		senate_concurres_url = 'http://www.lsc.state.oh.us/status128/scr.xls'
		files = [senate_bills_url, senate_jointres_url, senate_concurres_url]

		for senate_file in files:

			senate_bills_file = urllib.urlopen(senate_file).read()
			f = open('oh_bills.xls','w')
			f.write(senate_bills_file)
			f.close()


			wb = xlrd.open_workbook('oh_bills.xls')
			sh = wb.sheet_by_index(0)

			senate_file = str(senate_file)
			if len(str(senate_file)) == 44:
				file_type = senate_file[len(senate_file) - 7:len(senate_file)-4]
			else:
				file_type = senate_file[len(senate_file) - 6:len(senate_file)-4]



			for rownum in range(1, sh.nrows):

				bill_id = file_type + str(int(rownum))
				bill_title = str(sh.cell(rownum, 3).value)
				bill = Bill( '128', 'lower', bill_id, bill_title)
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
						elif coltitle.split()[0] == 'Gov.':
							actor = "Governor"
						elif coltitle.split()[-1] == 'Gov.':
							actor = "Governor"
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

				bill.add_source(senate_file)
				self.scrape_votes(bill, file_type, rownum)

				self.save_bill(bill)


	def scrape_votes(self, bill, file_type, number):


		self.follow_robots = False;

		vote_url = 'http://www.legislature.state.oh.us/votes.cfm?ID=128_' + file_type + '_' + str(number)
		
		with self.urlopen(vote_url) as page:
			root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
			
			for el in root.xpath('/html/body/table/tr[3]/td/table/tr[1]/td[2][@class="bigPanel"]/blockquote/font/table'):

				#need to insert a loop to go though every other row
				for mr in root.xpath('/html/body/table/tr[3]/td/table/tr[1]/td[2][@class="bigPanel"]/blockquote/font/table/tr/td/font'):
					print "inner loop"
					date = mr.path('string(/a)')
					#date = el.xpath('string(td[2]/font)')
					#date = mr.xpath('string(tr[2]/td[1]/font/a)')
					#motion = mr.xpath('string(tr[2]/td[2]/font)')
					#motion = motion.rpartition(motion.split()[-1])[0]
					print date
					#print motion

				



