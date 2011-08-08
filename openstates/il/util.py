# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulSoup

def get_soup(scraper, url):
    """Consolidate the code for getting a cached HTML page, and also tuck in the given url cause that's handy."""
    s = BeautifulSoup(scraper.urlopen(url))
    s.orig_url = url
    return s

