from nose.tools import *

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.mo.bills import MOBillScraper

import datetime
import urllib2
import scrapelib
import contextlib
import os
from mox import *
from test_utils import *

class MyMOBillScraper(MOBillScraper):
    def __init__(self,options):
        MOBillScraper.__init__(self,options)
        self.bills = []
    def save_bill(self,bill):
        self.bills.append(bill)
    def reset(self):
        self.bills = []


def test_senate():
    scraper = MyMOBillScraper({})
    m = Mox()
    m.StubOutWithMock(scraper,'urlopen')
    # 1. Get the list of senate bills
    scraper.urlopen(StrContains('BillList.aspx')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/bills-senate.html' % os.getcwd()))
    # 2. get a bill that has no cosponsor
    scraper.urlopen(StrContains('Bill.aspx')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetail.html' % os.getcwd()))
    # The first bill, is also passed:
    scraper.urlopen(StrContains('Actions.aspx')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billactionspassed.html' % os.getcwd()))
    # 3. for the rest of the bills, get one that has a cosponsor
    scraper.urlopen(StrContains('Bill.aspx')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetailwithcosponsor.html' % os.getcwd()))
    scraper.urlopen(StrContains('Actions.aspx')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billactions.html' % os.getcwd()))
    scraper.urlopen(StrContains('BillText.aspx')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billversions.html' % os.getcwd()))
    scraper.urlopen(StrContains('CoSponsors.aspx')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billcosponsor.html' % os.getcwd()))
    m.ReplayAll()
    scraper.scrape_senate('2011')
    eq_(477,len(scraper.bills))
    eq_('SB 70',scraper.bills[0]['bill_id'])
    eq_('http://www.senate.mo.gov/11info/BTS_Web/Bill.aspx?SessionType=R&BillID=4065289',scraper.bills[0]['bill_url'])
    eq_('CCS SS SCS SB 70',scraper.bills[0]['official_title'])
    # so the first bill has no cosponsor - so only one sponsor
    eq_(1,len(scraper.bills[0]['sponsors']))
    eq_('Schaefer',scraper.bills[0]['sponsors'][0]['name'])
    eq_('http://www.senate.mo.gov/11info/members/mem19.htm',scraper.bills[0]['sponsors'][0]['sponsor_link'])
    eq_(43,len(scraper.bills[0]['actions']))
    # make sure that the different kinds of 'actions' are properly categorized:
    eq_('upper',scraper.bills[0]['actions'][0]['actor'])     # Prefiled is the upper
    eq_('lower',scraper.bills[0]['actions'][-11]['actor'])   # 'H' (house) did something to it.
    eq_('upper',scraper.bills[0]['actions'][-10]['actor'])   # 'S' (senate) did something to it.
    eq_('upper',scraper.bills[0]['actions'][-4]['actor'])    # senate signed it
    eq_('lower',scraper.bills[0]['actions'][-3]['actor'])    # house signed it
    eq_('Governor',scraper.bills[0]['actions'][-2]['actor']) # governor dealt with it
    eq_('Governor',scraper.bills[0]['actions'][-1]['actor']) # governor dealt with it
    # versions!
    eq_(4,len(scraper.bills[0]['versions']))
    eq_('Introduced',scraper.bills[0]['versions'][0]['name'])
    eq_('http://www.senate.mo.gov/11info/pdf-bill/intro/SB70.pdf',scraper.bills[0]['versions'][0]['url'])
    eq_('Truly Agreed To and Finally Passed',scraper.bills[0]['versions'][-1]['name'])
    eq_('http://www.senate.mo.gov/11info/pdf-bill/tat/SB70.pdf',scraper.bills[0]['versions'][-1]['url'])

    # every additional bill will have a sponsor and a cosponsor
    eq_(2,len(scraper.bills[1]['sponsors']))
    eq_('McKenna',scraper.bills[1]['sponsors'][0]['name'])
    eq_('http://www.senate.mo.gov/11info/members/mem22.htm',scraper.bills[1]['sponsors'][0]['sponsor_link'])
    eq_('cosponsor',scraper.bills[1]['sponsors'][1]['type'])
    eq_('John Lamping',scraper.bills[1]['sponsors'][1]['name'])
    eq_('http://www.senate.mo.gov/11info/members/mem24.htm',scraper.bills[1]['sponsors'][1]['sponsor_link'])
    eq_(11,len(scraper.bills[1]['actions']))
    eq_('upper',scraper.bills[1]['actions'][7]['actor'])
    eq_(datetime.datetime(2011,2,22),scraper.bills[1]['actions'][7]['date'])
    eq_('Bill Placed on Informal Calendar',scraper.bills[1]['actions'][7]['action'])
    m.UnsetStubs()
    m.VerifyAll()

def test_house():
    scraper = MyMOBillScraper({})
    m = Mox()
    m.StubOutWithMock(scraper,'urlopen')
    # first, get the list of all house bills for the given year.
    scraper.urlopen(StrContains('BillList.aspx?year=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/bills-house.html' % os.getcwd()))

    # then the details...
    # the first one in the list has a funky text (non standard)
    scraper.urlopen(StrContains('billsummaryprn.aspx?bill=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetail2-house.html' % os.getcwd()))
    scraper.urlopen(Regex('^.*biltxt\/intro\/HB.*$')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billtext2-house.html' % os.getcwd()))
    scraper.urlopen(StrContains('BillActionsPrn.aspx?bill=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billactions-house.html' % os.getcwd()))

    # the second one doesn't have text:
    scraper.urlopen(StrContains('billsummaryprn.aspx?bill=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetail-house.html' % os.getcwd()))
    scraper.urlopen(Regex('^.*biltxt\/intro\/HB.*$')) \
            .AndRaise(scrapelib.HTTPError(scrapelib.Response('url','url'),None))
    scraper.urlopen(StrContains('BillActionsPrn.aspx?bill=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billactions-house.html' % os.getcwd()))

    # the third one doesn't have or a summary page to begin with:
    scraper.urlopen(StrContains('billsummaryprn.aspx?bill=')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetail3-house.html' % os.getcwd()))
    #scraper.urlopen(Regex('^.*biltxt\/intro\/HB.*$')) \
            #.AndRaise(scrapelib.HTTPError(scrapelib.Response('url','url'),None))

    # do the rest are normal/fine:
    scraper.urlopen(StrContains('billsummaryprn.aspx?bill=')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billdetail-house.html' % os.getcwd()))
    scraper.urlopen(Regex('^.*biltxt\/intro\/HB.*$')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billtext-house.html' % os.getcwd()))
    scraper.urlopen(StrContains('BillActionsPrn.aspx?bill=')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/billactions-house.html' % os.getcwd()))

    m.ReplayAll()
    scraper.scrape_house('2011')

    eq_(1143,len(scraper.bills))
    eq_(2,len(scraper.bad_urls))

    # the first bill is mostly standard.
    eq_('HB 26',scraper.bills[0]['bill_id'])
    eq_('http://www.house.mo.gov/billsummaryprn.aspx?bill=HB1&year=2011&code=R',scraper.bills[0]['bill_url'])
    eq_('HB 26',scraper.bills[0]['official_title'])
    eq_(2,len(scraper.bills[0]['sponsors']))
    eq_('Jones, Tishaura',scraper.bills[0]['sponsors'][0]['name'])
    eq_('KANDER',scraper.bills[0]['sponsors'][1]['name'])
    eq_('http://www.house.mo.gov/member.aspx?district=063&year=2011',scraper.bills[0]['sponsors'][0]['sponsor_link'])

    # the second bill doesn't have any cosponsor info.
    eq_('HB 45',scraper.bills[1]['bill_id'])
    eq_('SS SCS HCS HB 45',scraper.bills[1]['official_title'])
    eq_('Hoskins, Denny',scraper.bills[1]['sponsors'][0]['name'])
    eq_('http://www.house.mo.gov/member.aspx?district=121&year=2011',scraper.bills[1]['sponsors'][0]['sponsor_link'])

    # the third bill doesn't have any info at all. It didn't get logged, but I've recorded
    # it in another data structure for later fixing maybe.

    # the rest of the bills are pretty detailed
    eq_(8,len(scraper.bills[2]['sponsors']))
    eq_('http://www.house.mo.gov/member.aspx?district=121&year=2011',scraper.bills[2]['sponsors'][0]['sponsor_link'])
    eq_('primary',scraper.bills[2]['sponsors'][0]['type'])
    eq_('cosponsor',scraper.bills[2]['sponsors'][1]['type'])
    eq_('ALLEN',scraper.bills[2]['sponsors'][1]['name'])
    eq_('SCHARNHORST',scraper.bills[2]['sponsors'][-1]['name'])

    eq_(42,len(scraper.bills[0]['actions']))
    eq_(1,len(scraper.bills[0]['versions']))
    eq_(5,len(scraper.bills[1]['versions']))
    eq_(['Introduced','Committee','Perfected','Senate Comm Sub','Truly Agreed'], [x['name'] for x in scraper.bills[1]['versions']])
    eq_('http://www.house.mo.gov/billtracking/bills111/biltxt/intro/HB0026I.htm',scraper.bills[0]['versions'][0]['url'])
    eq_('Introduced',scraper.bills[0]['versions'][-1]['name'])
    eq_('Truly Agreed',scraper.bills[1]['versions'][-1]['name'])
    eq_('http://www.house.mo.gov/billtracking/bills111/biltxt/intro/HB0045I.htm',scraper.bills[1]['versions'][0]['url'])
    eq_('http://www.house.mo.gov/billtracking/bills111/biltxt/truly/HB0045T.htm',scraper.bills[1]['versions'][-1]['url'])
    m.UnsetStubs()
    m.VerifyAll()
