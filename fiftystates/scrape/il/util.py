# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulSoup
from pyutils.legislation import LegislationScraper


# class util_scraper(LegislationScraper):
#     state = 'il'
# 
# scraper_cacher = util_scraper()

def get_text(soup):
    if isinstance(soup,str) or isinstance(soup,unicode): s = soup
    else: s = "".join(soup(text=True))
    return s.replace("\n","")
        
def get_soup(scraper, url):
    """Consolidate the code for getting a cached HTML page, and also tuck in the given url cause that's handy."""
    s = BeautifulSoup(scraper.urlopen(url))
    s.orig_url = url
    return s

def elem_name(x):
    """Given something which may be a BeautifulSoup element, return its name (e.g. 'a','span', etc) or None if it isn't an element.
    """
    try:        
        return x.name
    except AttributeError:
        return None

def standardize_chamber(s):
    if s is not None:
        if s.lower() == 'house':
            return 'lower'
        if s.lower() == 'senate':
            return 'upper'
    return s