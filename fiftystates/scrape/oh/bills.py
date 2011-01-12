from __future__ import with_statement

import urlparse
import datetime

from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

import xlrd
import scrapelib
import lxml.etree


class OHBillScraper(BillScraper):
    state = 'oh'

    def scrape(self, chamber, session):
        if int(session) < 128:
            raise NoDataForPeriod(year)

        base_url = 'http://www.lsc.state.oh.us/status%s/' % session

        bill_types = {'lower': ['hb', 'hjr', 'hcr'],
                      'upper': ['sb', 'sjr', 'scr']}

        for bill_type in bill_types[chamber]:
            url = base_url + '%s.xls' % bill_type

            try:
                fname, resp = self.urlretrieve(url)
            except scrapelib.HTTPError:
                # if there haven't yet been any bills of a given type
                # then the excel url for that type will 404
                continue

            sh = xlrd.open_workbook(fname).sheet_by_index(0)

            for rownum in range(1, sh.nrows):
                bill_id = '%s %s' % (bill_type.upper(), rownum)
                bill_title = str(sh.cell(rownum, 3).value)
                bill = Bill(session, chamber, bill_id, bill_title)
                bill.add_source(url)
                bill.add_sponsor('primary', str(sh.cell(rownum, 1).value))

                # add cosponsor
                if sh.cell(rownum, 2).value:
                    bill.add_sponsor('cosponsor',
                                     str(sh.cell(rownum, 2).value))

                actor = ""

                # Actions start column after bill title
                for colnum in range(4, sh.ncols - 1):
                    action = str(sh.cell(0, colnum).value)
                    cell = sh.cell(rownum, colnum)
                    date = cell.value

                    if len(action) != 0:
                        if action.split()[0] == 'House':
                            actor = "lower"
                        elif action.split()[0] == 'Senate':
                            actor = "upper"
                        elif action.split()[-1] == 'Governor':
                            actor = "governor"
                        elif action.split()[0] == 'Gov.':
                            actor = "governor"
                        elif action.split()[-1] == 'Gov.':
                            actor = "governor"

                    if type(date) == float:
                        date = str(xlrd.xldate_as_tuple(date, 0))
                        date = datetime.datetime.strptime(
                            date, "(%Y, %m, %d, %H, %M, %S)")
                        bill.add_action(actor, action, date)

                self.scrape_votes(bill, bill_type, rownum, session)
                self.save_bill(bill)

    def scrape_votes(self, bill, bill_type, number, session):
        vote_url = ('http://www.legislature.state.oh.us/votes.cfm?ID=' +
                    session + '_' + bill_type + '_' + str(number))

        with self.urlopen(vote_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            save_date = None
            for el in root.xpath('/html/body/table/tr[3]/td/table/tr[1]/td[2]'
                                 '[@class="bigPanel"]/blockquote/font/table'):

                for mr in root.xpath('/html/body/table/tr[3]/td/table/tr[1]'
                                     '/td[2][@class="bigPanel"]/blockquote/'
                                     'font/table/tr[position() > 1]'):

                    yes_count = 0
                    yes_placement = 0
                    no_count = 0
                    no_placement = 0

                    date = mr.xpath('string(td/font/a)')
                    date = date.lstrip()
                    date = date.rstrip()
                    info = mr.xpath('string(td[2]/font)')

                    # makes sure that date is saved
                    if len(date.split()) > 0:
                        date = datetime.datetime.strptime(date, "%m/%d/%Y")
                        save_date = date

                    if info.split()[0] == 'Yeas':
                        yes_count = info.split()[2]

                        # no votes
                        for voter in range(3, len(info.split())):
                            if info.split()[voter] == '-':
                                no_count = info.split()[voter + 1]
                                no_placement = voter + 2
                                yes_placement = voter - 2

                    # motion and chamber
                    if info.split()[-1] == 'details':
                        motion = info[0:-10]
                        motion = motion.lstrip()
                        motion = motion.rstrip()
                        chamber = motion.split()[0]

                        if chamber == "Senate":
                            chamber = "upper"
                        else:
                            chamber = "lower"

                    if yes_count > no_count:
                        passed = True
                    else:
                        passed = False

                    vote = Vote(chamber, save_date, motion, passed,
                                int(yes_count), int(no_count), 0)

                    for voters in range(3, yes_placement):
                        legis = ""
                        initials = 0

                        # check to see if the next name is actually an initial
                        if len(info.split()[voters + 1]) < 2:
                            legis = (legis + info.split()[voters] + " " +
                                     info.split()[voters + 1])
                        elif len(info.split()[voters]) < 2:
                            initials = 1
                        else:
                            legis = legis + info.split()[voters]

                        if initials < 1:
                            vote.yes(legis)

                    for voters in range(no_placement, len(info.split())):
                        legis = ""
                        initials = 0

                        # check to see if the next name is actually an initial
                        if ((info.split()[voters] != info.split()[-1]) and
                            (len(info.split()[voters + 1]) < 2)):

                            legis = (legis + info.split()[voters] + " " +
                                     info.split()[voters + 1])
                        elif len(info.split()[voters]) < 2:
                            initals = 1
                        else:
                            legis = legis + info.split()[voters]

                        if initials < 1:
                            vote.no(legis)

                    # ignore rid of blank votes
                    if yes_count > 0 or no_count > 0:
                        vote.add_source(vote_url)
                        bill.add_vote(vote)
