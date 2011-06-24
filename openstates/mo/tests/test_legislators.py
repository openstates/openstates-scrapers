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

    def urlopen(self,url):
        return contextlib.closing(ClosableString(urllib2.urlopen(url).read()))
    def save_legislator(self,leg):
        self.legs.append(leg)
    def save_vacant_legislator(self,leg):
        self.vac_legs.append(leg)

def test_reps():
    scraper = MyMOLegislatorScraper({})
    scraper.reps_url = 'file://%s/openstates/mo/tests/member%s.aspx' % (os.getcwd(),'%s')

    # scrape the current year: there are three vacancies...
    scraper.scrape_reps('lower','2011','')
    eq_(len(scraper.legs),160)
    eq_(scraper.legs[-2]['full_name'],'Zachary Wyatt')
    eq_(scraper.legs[-2]['roles'][0]['district'],'2')
    eq_(scraper.legs[-2]['roles'][0]['party'],'Republican')
    eq_(len(scraper.vac_legs),3)
    eq_(scraper.vac_legs[-1]['roles'][0]['district'],'83')
    eq_(scraper.vac_legs[-1]['roles'][0]['party'],'')

    # scraping 2000 - fewer vacant seats
    scraper.legs = []
    scraper.vac_legs = []
    scraper.scrape_reps('lower','2000','')
    eq_(len(scraper.legs),70)
    eq_(len(scraper.vac_legs),93)

    # TODO scraping 1900 just times out when I do it in the browser. How would I test for this?
    #scraper.scrape_reps('lower','1900','')
    
# vim: set sw=4 ts=4 fdm=marker :
