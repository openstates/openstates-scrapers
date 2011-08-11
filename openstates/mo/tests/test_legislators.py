from nose.tools import *

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.mo.legislators import MOLegislatorScraper

import urllib2
import contextlib
import os
from mox import *
from test_utils import *

class MyMOLegislatorScraper(MOLegislatorScraper):
    def __init__(self,options):
        MOLegislatorScraper.__init__(self,options)
        self.legs = []
        self.vac_legs = []
    def save_legislator(self,leg):
        self.legs.append(leg)
    def save_vacant_legislator(self,leg):
        self.vac_legs.append(leg)
    def reset(self):
        self.legs = []
        self.vac_legs = []

def test_senators():
    scraper = MyMOLegislatorScraper({})
    m = Mox()
    m.StubOutWithMock(scraper,'urlopen')
    # Expect:
    # 1. one call to obtain a list of senators
    # For each senator:
    #   - one call to their 'details' page
    #   - one call to their 'address' page.
    scraper.urlopen(StrContains('11info/senalpha.htm')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-2011senatelist.html' % os.getcwd()))
    # this member has an email and standard committees:
    scraper.urlopen(StrContains('members/mem')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetails.html' % os.getcwd()))
    scraper.urlopen(StrContains('OfficeInfo.htm')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetailsofficeinfo.html' % os.getcwd()))
    # the rest don't have emails, and have slightly different committee listings:
    scraper.urlopen(StrContains('members/mem')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetails2.html' % os.getcwd()))
    scraper.urlopen(StrContains('OfficeInfo.htm')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetailsofficeinfo2.html' % os.getcwd()))
    m.ReplayAll()
    scraper.scrape_senators('upper','2011','')
    eq_(len(scraper.legs),6)

    # someone with full details and standard committees:
    eq_(7,len(scraper.legs[0]['roles']))
    eq_(scraper.legs[0]['full_name'],'Dan Brown')
    eq_(scraper.legs[0]['photo_url'],'http://www.senate.mo.gov/11info/graphics/d16-photo.gif')
    eq_(scraper.legs[0]['email'],'Dan.Brown@senate.mo.gov')
    eq_(scraper.legs[0]['office_address'],u'\xa0\xa0201 W Capitol Ave., Rm. 434\r\xa0\xa0Jefferson City, Missouri  65101\r')
    eq_(scraper.legs[0]['roles'][0]['district'],'16')
    eq_(scraper.legs[0]['roles'][0]['party'],'Republican')
    eq_(scraper.legs[0]['roles'][1]['committee'],'Agriculture, Food Production & Outdoor Resources')
    eq_(scraper.legs[0]['roles'][2]['committee'],'Appropriations')
    eq_(scraper.legs[0]['roles'][3]['committee'],'Education')
    eq_(scraper.legs[0]['roles'][4]['committee'],'Veterans\' Affairs, Emerging Issues, Pensions & Urban Affairs')
    eq_(scraper.legs[0]['roles'][5]['committee'],'Joint Committee on Life Sciences')
    assert 'subcommittee' not in scraper.legs[0]['roles'][5]
    eq_(scraper.legs[0]['roles'][6]['committee'],'Senate Interim Committee on Natural Disaster Recovery')
    eq_(scraper.legs[0]['roles'][6]['subcommittee'],'Sub Committee on Fiscal Response')
    # TODO verify that there are three sources for each person

    # someone w/o an email address:
    eq_(scraper.legs[1]['full_name'],'Victor Callahan')
    eq_(scraper.legs[1]['photo_url'],'http://www.senate.mo.gov/11info/graphics/d19-photo.gif')
    assert 'email' not in scraper.legs[1]
    eq_(scraper.legs[1]['office_address'],u'\xa0\xa0201 W Capitol Ave., Rm. 333\r  \xa0\xa0Jefferson City, Missouri  65101\r')
    eq_(11,len(scraper.legs[1]['roles']))
    eq_(scraper.legs[1]['roles'][0]['district'],'11')
    eq_(scraper.legs[1]['roles'][0]['party'],'Democratic')
    eq_(scraper.legs[1]['roles'][1]['committee'],'Appropriations')
    eq_(scraper.legs[1]['roles'][2]['committee'],'Commerce, Consumer Protection, Energy and the Environment')
    eq_(scraper.legs[1]['roles'][3]['committee'],'Education')
    eq_(scraper.legs[1]['roles'][4]['committee'],'Joint Committee on Capital Improvements & Leases Oversight')
    eq_(scraper.legs[1]['roles'][5]['committee'],'Joint Committee on Education')
    eq_(scraper.legs[1]['roles'][6]['committee'],'Joint Legislative Committee on Court Automation')
    eq_(scraper.legs[1]['roles'][7]['committee'],'Joint Committee on Government Accountability')
    eq_(scraper.legs[1]['roles'][8]['committee'],'Joint Committee on Legislative Research')
    eq_(scraper.legs[1]['roles'][9]['committee'],'Joint Committee on MO Healthnet')
    eq_(scraper.legs[1]['roles'][10]['committee'],'Senate Interim Committee on Natural Disaster Recovery')
    eq_(scraper.legs[1]['roles'][10]['subcommittee'],'Sub Committee on Fiscal Response')
    m.UnsetStubs()
    m.VerifyAll()

def test_reps():
    scraper = MyMOLegislatorScraper({})
    m = Mox()
    m.StubOutWithMock(scraper,'urlopen')
    scraper.urlopen(Regex('^.*gov\/member.aspx\?year=2011$')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/member2011.aspx' % os.getcwd()))
    scraper.urlopen(Regex('^.*gov\/member.aspx\?year=2011&district=.*$')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/memberdetailsfull.aspx' % os.getcwd()))
    scraper.urlopen(Regex('^.*gov\/member.aspx\?year=2011&district=.*$')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/memberdetailsvacant.aspx' % os.getcwd()))
    m.ReplayAll()
    scraper.scrape_reps('lower','2011','')
    eq_(len(scraper.legs),160)
    # 1. first legislater has full details
    eq_(scraper.legs[0]['full_name'],'Sue Allen')
    eq_(scraper.legs[0]['photo_url'],'http://www.house.mo.gov/billtracking/bills101/member/mem104.jpg')
    eq_(scraper.legs[0]['email'],'Joe.FallertJr@house.mo.gov')
    eq_(7,len(scraper.legs[0]['roles']))
    eq_(scraper.legs[0]['roles'][0]['district'],'92')
    eq_(scraper.legs[0]['roles'][0]['party'],'Republican')
    eq_(scraper.legs[0]['roles'][1]['committee'],'Joint Committee on Legislative Research')
    eq_(scraper.legs[0]['roles'][2]['committee'],'Fiscal Review')
    eq_(scraper.legs[0]['roles'][3]['committee'],'Administration and Accounts')
    eq_(scraper.legs[0]['roles'][4]['committee'],'Elections')
    eq_(scraper.legs[0]['roles'][5]['committee'],'Transportation')
    eq_(scraper.legs[0]['roles'][6]['committee'],'Tourism and Natural Resources')
    # 2. the rest have no additional details 
    assert 'email' not in scraper.legs[-1]
    assert 'photo_url' not in scraper.legs[-1]
    eq_(1,len(scraper.legs[-1]['roles']))
    # 3. and there are three vacancies...
    eq_(len(scraper.vac_legs),3)
    eq_(scraper.vac_legs[-1]['roles'][0]['district'],'83')
    eq_(scraper.vac_legs[-1]['roles'][0]['party'],'')
    m.UnsetStubs()
    m.VerifyAll()
    # TODO verify that there are two sources for each person

    # 4. some reference picture URLs that don't exist (404)
    # TODO question: if the state site gives a page that doesn't exist (as in this case) should I verify the
    # link before I publish it to billy?

    # scraping 2000 - many more vacant seats
    scraper.reset()
    m.StubOutWithMock(scraper,'urlopen')
    scraper.urlopen(StrContains('gov/member.aspx?year=2000')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/member2000.aspx' % os.getcwd()))
    scraper.urlopen(StrContains('gov/member.aspx?year=2000&district')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/memberdetailsfull.aspx' % os.getcwd()))
    m.ReplayAll()
    scraper.scrape_reps('lower','2000','')
    eq_(len(scraper.legs),70)
    eq_(len(scraper.vac_legs),93)

    m.UnsetStubs()
    m.VerifyAll()
    
# vim: set sw=4 ts=4 fdm=marker :
