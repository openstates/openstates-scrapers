import re
import urllib2

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class CACommitteeScraper(CommitteeScraper):
    state = 'ca'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            self.scrape_upper_committees(term)
        elif chamber == 'lower':
            self.scrape_lower_committees(term)

    def scrape_upper_committees(self, term):
        url = "http://senate.ca.gov/committees"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//h3[. = 'Standing Committees']/..//a"):
                if not link.text:
                    continue

                comm = Committee('upper',
                                 'Committee on %s' % link.text.strip())
                self.scrape_upper_committee_members(comm, link.attrib['href'])
                self.save_committee(comm)

            for link in page.xpath("//h3[. = 'Select Committees']/..//a"):
                if not link.text:
                    continue

                comm = Committee('upper',
                                 'Select Committee on %s' % link.text.strip())
                self.scrape_upper_committee_members(comm, link.attrib['href'])
                self.save_committee(comm)

    def scrape_upper_committee_members(self, committee, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            committee.add_source(url)

            for link in page.xpath("//a[contains(., 'Senator')]"):
                name = link.text.strip().replace('Senator ', '')

                match = re.search(r'(.+)\s+\(((Vice )?Chair)\)$', name)
                if match:
                    role = match.group(2).lower()
                    name = match.group(1)
                else:
                    role = 'member'

                committee.add_member(name, role)

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

                if comm['members']:
                    self.save_committee(comm)

    def scrape_lower_committee_members(self, committee, url):
        # break out of frame
        url = url.replace('newcomframeset.asp', 'welcome.asp')
        committee.add_source(url)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for a in page.xpath('//tr/td/font/a'):
                if re.match('^(mailto:)', a.attrib['href']):
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
