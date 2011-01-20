import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class AKCommitteeScraper(CommitteeScraper):
    state = 'ak'

    def scrape(self, chamber, term):
        url = ("http://www.legis.state.ak.us/basis/commbr_info.asp"
               "?session=%s" % term)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

            for link in page.xpath("//a[contains(@href, 'comm=')]"):
                name = link.text.strip()

                if name.startswith('CONFERENCE COMMITTEE'):
                    continue

                url = link.attrib['href']
                if ('comm=%s' % chamber_abbrev) in url:
                    self.scrape_committee(chamber, name, url)

    def scrape_committee(self, chamber, name, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            if page.xpath("//h3[. = 'Joint Committee']"):
                chamber = 'joint'

            comm = Committee(chamber, name)
            comm.add_source(url)

            for link in page.xpath("//a[contains(@href, 'member=')]"):
                member = link.text.strip()

                mtype = link.xpath("string(../preceding-sibling::td[1])")
                mtype = mtype.strip(": \r\n\t").lower()

                comm.add_member(member, mtype)

            self.save_committee(comm)
