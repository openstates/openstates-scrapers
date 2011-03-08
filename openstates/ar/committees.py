from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html
import urllib, urlparse

COMM_TYPES = {'joint': 'Joint',
              # 'task_force': 'Task Force',
              'upper': 'Senate',
              'lower': 'House'}

class ARCommitteeScraper(CommitteeScraper):
    state = 'ar'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod

        base_url = ('http://www.arkleg.state.ar.us/assembly/2011/2011R/Pages/Committees.aspx?committeetype=')

        for chamber, url_ext in COMM_TYPES.iteritems():
            chamber_url = url_fix(base_url + url_ext)
            with self.urlopen(chamber_url) as page:
                page = lxml.html.fromstring(page)

                for a in page.xpath('//td[@class="dxtl dxtl__B0"] \
                                      /a'):
                    name = a.text
                    comm_url = url_fix(a.attrib['href'])
                    if chamber == 'task_force':
                        chamber = 'joint'
                    self.scrape_committee(chamber, name, comm_url)


    def scrape_committee(self, chamber, name, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            comm = Committee(chamber, name)
            comm.add_source(url)

            for tr in page.xpath('//table[@class="gridtable"] \
                                   /tr[position()>1]'):
                if tr.xpath('string(td[1])'):
                    mtype = tr.xpath('string(td[1])')
                else:
                    mtype = 'member'
                member = tr.xpath('string(td[3])').split()
                member = ' '.join(member[1:])
                comm.add_member(member, mtype)

            self.save_committee(comm)

def url_fix(s, charset='utf-8'):
    """http://stackoverflow.com/questions/120951/how-can-i-normalize-a-url-in-python"""
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))
