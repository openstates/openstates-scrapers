from nose.tools import *

from openstates.mo.legislators import MOLegislatorScraper

import urllib2
import contextlib
import os

class ClosableString(str):
    def close(self):
        return self

class MyMOLegislatorScraper(MOLegislatorScraper):
    legs = []
    vac_legs = []
    # for the details URL I'll just loop oveer these three common variations of
    # the details page:
    member_details_options = [ 'memberdetailsfull', 'memberdetailsnopic', 'memberdetailsvacant' ]

    def urlopen(self,url):
        if url.startswith("memberdetails"):
            return contextlib.closing(ClosableString(urllib2.urlopen(
                'file://%s/openstates/mo/tests/%s.aspx' % (os.getcwd(),self.member_details_options[len(self.legs) % 3])
            ).read()))
        return contextlib.closing(ClosableString(urllib2.urlopen(url).read()))
    def get_senator_url(self,session):
        return 'file://%s/openstates/mo/tests/11-2011senatelist.html' % (os.getcwd())
    def get_senator_list_url(self,session,district):
        return 'file://%s/openstates/mo/tests/11-senatordetails.html' % (os.getcwd())
    def get_senator_address_url(self,session,key):
        return 'file://%s/openstates/mo/tests/11-senatordetailsofficeinfo.html' % (os.getcwd())
    def save_legislator(self,leg):
        self.legs.append(leg)
    def save_vacant_legislator(self,leg):
        self.vac_legs.append(leg)
    def reset(self):
        self.legs = []
        self.vac_legs = []

def test_senators():
    scraper = MyMOLegislatorScraper({})
    scraper.reset()
    scraper.senator_details_url = 'file://%s/openstates/mo/tests/%s-senatordetails.html' % (os.getcwd(),'%s')
    scraper.scrape_senators('upper','2011','')
    eq_(len(scraper.legs),34)
    eq_(scraper.legs[-1]['full_name'],'Robin Wright-Jones')
    eq_(scraper.legs[-1]['photo_url'],'http://www.senate.mo.gov/11info/graphics/d16-photo.gif')
    eq_(scraper.legs[-1]['email'],'Dan.Brown@senate.mo.gov')
    eq_(scraper.legs[-1]['roles'][0]['district'],'5')
    eq_(scraper.legs[-1]['roles'][0]['party'],'Democratic')

def test_reps():
    scraper = MyMOLegislatorScraper({})
    scraper.reset()
    scraper.reps_url = 'file://%s/openstates/mo/tests/member%s.aspx' % (os.getcwd(),'%s')
    scraper.rep_details_url = 'memberdetails%s%s'

    # scrape the current year: there are three vacancies...
    scraper.scrape_reps('lower','2011','')
    eq_(len(scraper.legs),160)
    eq_(scraper.legs[-1]['full_name'],'Anne Zerr')
    eq_(scraper.legs[-1]['photo_url'],'http://www.house.mo.gov/billtracking/bills101/member/mem104.jpg')
    eq_(scraper.legs[-1]['email'],'Joe.FallertJr@house.mo.gov')
    eq_(scraper.legs[-1]['roles'][0]['district'],'18')
    eq_(scraper.legs[-1]['roles'][0]['party'],'Republican')
    # test the other two kinds of detail pages I encountered:
    # 1. no details found
    eq_(scraper.legs[-2]['photo_url'],None)
    eq_(scraper.legs[-2]['email'],None)
    # 2. no picture found (doesn't seem to matter)
    # TODO question: if the state site gives a page that doesn't exist (as in this case) should I verify the
    # link before I publish it to billy?
    eq_(scraper.legs[-3]['photo_url'],'http://www.house.mo.gov/billtracking/bills031/member/mem100.jpg')
    eq_(scraper.legs[-3]['email'],'Sue.Schoemehl@house.mo.gov')
    eq_(len(scraper.vac_legs),3)
    eq_(scraper.vac_legs[-1]['roles'][0]['district'],'83')
    eq_(scraper.vac_legs[-1]['roles'][0]['party'],'')

    # scraping 2000 - fewer vacant seats
    scraper.reset()
    scraper.scrape_reps('lower','2000','')
    eq_(len(scraper.legs),70)
    eq_(len(scraper.vac_legs),93)

    # TODO scraping 1900 just times out when I do it in the browser. How would I test for this?
    #scraper.scrape_reps('lower','1900','')
    
# vim: set sw=4 ts=4 fdm=marker :
