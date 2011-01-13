import re
import urllib2

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.committees import CommitteeScraper, Committee

import lxml.html


class CACommitteeScraper(CommitteeScraper):
    state = 'ca'

    def scrape(self, chamber, term):
        if term != '20112012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_upper_committees(term)
        else:
            self.scrape_lower_committees(term)

    def scrape_upper_committees(self, term):
        types = {
            'standing':
            'http://www.sen.ca.gov/~newsen/committees/standing.htp',
            'select':
            'http://www.sen.ca.gov/~newsen/committees/Select.HTP'}
        comm_xpath = '//a[contains(@href, "PROFILE.HTM")]'

        for type, url in types.items():
            with self.urlopen(url) as page:
                page = lxml.html.fromstring(page)
                page.make_links_absolute(url)

                for a in page.xpath(comm_xpath):
                    name = a.text.strip()

                    if type == 'select':
                        name = 'Select Committee on ' + name
                    else:
                        name = 'Committee on ' + name

                    comm = Committee('upper', name)
                    comm['type'] = type
                    self.scrape_upper_committee_members(
                        comm, a.attrib['href'])
                    self.save_committee(comm)

    def scrape_upper_committee_members(self, comm, url):
        # Senate committee pages are being served up with
        # an incorrect Content-Length header that confuses
        # httplib/httplib2, so fall back to urllib2
        page = urllib2.urlopen(url).read()
        page = lxml.html.fromstring(page)
        comm.add_source(url)

        for a in page.xpath('//a[contains(@href, "district")]'):
            name = a.text.strip()
            name = name.replace('Senator ', '')

            if name.endswith(' (Chair)'):
                mtype = 'chair'
                name = name.replace(' (Chair)', '')
            elif name.endswith(' (Vice-Chair)'):
                mtype = 'vice-chair'
                name = name.replace(' (Vice-Chair)', '')
            else:
                mtype = 'member'

            comm.add_member(name, mtype)

    def scrape_lower_committees(self, term):
        list_url = 'http://www.assembly.ca.gov/acs/comDir.asp'
        with self.urlopen(list_url) as list_page:
            list_page = lxml.html.fromstring(list_page)
            list_page.make_links_absolute(list_url)

            for a in list_page.xpath('//ul/a'):
                name = a.text.strip()
                name = name.replace(u'\u0092', "'")

                if re.search(r' X\d$', name):
                    continue

                if name.startswith('Joint'):
                    comm_chamber = 'joint'
                else:
                    comm_chamber = 'lower'

                comm = Committee(comm_chamber, name)
                self.scrape_lower_committee_members(comm,
                                                    a.attrib['href'])
                self.save_committee(comm)

    def scrape_lower_committee_members(self, committee, url):
        # break out of frame
        url = url.replace('newcomframeset.asp', 'welcome.asp')
        committee.add_source(url)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for a in page.xpath('//tr/td/font/a'):
                if re.match('^(mailto:|javascript:)', a.attrib['href']):
                    continue

                name = a.xpath('string(ul)').strip()
                name = re.sub('\s+', ' ', name)

                parts = name.split('-', 2)
                if len(parts) > 1:
                    name = parts[0].strip()
                    mtype = parts[1].strip().lower()
                else:
                    mtype = 'member'

                if not name:
                    self.warning("Empty member name")
                    continue

                committee.add_member(name, mtype)
