from nose.tools import *

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.mo.legislators import MOLegislatorScraper

import urllib2
import contextlib
import os
from mox import *

class ClosableString(str):
    def close(self):
        return self

def openFile(url):
    return contextlib.closing(ClosableString(urllib2.urlopen(url).read()))

class MyMOLegislatorScraper(MOLegislatorScraper):
    def __init__(self,options):
        MOLegislatorScraper.__init__(self,options)
        self.legs = []
        self.vac_legs = []
    def save_legislator(self,leg):
        self.legs.append(leg)
        #print "leg = %s" % leg
        #LegislatorScraper.validate_json(self,leg)
    def save_vacant_legislator(self,leg):
        self.vac_legs.append(leg)
    def reset(self):
        #self.output_dir = 'data/mo/'
        self.legs = []
        self.vac_legs = []

def test_senators():
    scraper = MyMOLegislatorScraper({})
    scraper.reset()
    m = Mox()
    m.StubOutWithMock(scraper,'urlopen')
    scraper.urlopen(StrContains('11info/senalpha.htm')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-2011senatelist.html' % os.getcwd()))
    scraper.urlopen(StrContains('members/mem')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetails.html' % os.getcwd()))
    scraper.urlopen(StrContains('OfficeInfo.htm')) \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetailsofficeinfo.html' % os.getcwd()))
    scraper.urlopen(StrContains('members/mem')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetails.html' % os.getcwd()))
    scraper.urlopen(StrContains('OfficeInfo.htm')) \
            .MultipleTimes() \
            .AndReturn(openFile('file://%s/openstates/mo/tests/11-senatordetailsofficeinfo2.html' % os.getcwd()))
    m.ReplayAll()
    scraper.scrape_senators('upper','2011','')
    eq_(len(scraper.legs),6)
    eq_(scraper.legs[0]['full_name'],'Dan Brown')
    eq_(scraper.legs[0]['photo_url'],'http://www.senate.mo.gov/11info/graphics/d16-photo.gif')
    eq_(scraper.legs[0]['email'],'Dan.Brown@senate.mo.gov')
    eq_(scraper.legs[0]['office_address'],u'\xa0\xa0201 W Capitol Ave., Rm. 434\r\xa0\xa0Jefferson City, Missouri  65101\r')
    eq_(scraper.legs[0]['roles'][0]['district'],'16')
    eq_(scraper.legs[0]['roles'][0]['party'],'Republican')
    eq_(scraper.legs[1]['full_name'],'Victor Callahan')
    eq_(scraper.legs[1]['photo_url'],'http://www.senate.mo.gov/11info/graphics/d16-photo.gif')
    assert 'email' not in scraper.legs[1]
    eq_(scraper.legs[1]['office_address'],u'\xa0\xa0201 W Capitol Ave., Rm. 333\r  \xa0\xa0Jefferson City, Missouri  65101\r')
    eq_(scraper.legs[1]['roles'][0]['district'],'11')
    eq_(scraper.legs[1]['roles'][0]['party'],'Democratic')
    m.UnsetStubs()
    m.VerifyAll()

def test_reps():
    scraper = MyMOLegislatorScraper({})
    scraper.reset()
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
    eq_(scraper.legs[0]['roles'][0]['district'],'92')
    eq_(scraper.legs[0]['roles'][0]['party'],'Republican')

    # 2. the rest have no additional details 
    assert 'email' not in scraper.legs[-1]
    assert 'photo_url' not in scraper.legs[-1]

    # 3. and there are three vacancies...
    eq_(len(scraper.vac_legs),3)
    eq_(scraper.vac_legs[-1]['roles'][0]['district'],'83')
    eq_(scraper.vac_legs[-1]['roles'][0]['party'],'')
    m.UnsetStubs()
    m.VerifyAll()

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
