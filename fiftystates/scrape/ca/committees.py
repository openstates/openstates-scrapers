import re

from fiftystates.scrape.committees import CommitteeScraper, Committee

import lxml.html


class CACommitteeScraper(CommitteeScraper):
    state = 'ca'

    def scrape(self, chamber, term):
        if chamber != 'lower' or term != '20092010':
            return

        list_url = 'http://www.assembly.ca.gov/acs/comDir.asp'
        with self.urlopen(list_url) as list_page:
            list_page = lxml.html.fromstring(list_page)
            list_page.make_links_absolute(list_url)

            for a in list_page.xpath('//ul/a'):
                name = a.text.strip()

                if re.search(r' X\d$', name):
                    continue

                if name.startswith('Joint'):
                    comm_chamber = 'joint'
                else:
                    comm_chamber = 'lower'

                comm = Committee(comm_chamber, a.text.strip())
                self.scrape_committee_members(comm, a.attrib['href'])
                self.save_committee(comm)

    def scrape_committee_members(self, committee, url):
        # break out of frame
        url = url.replace('newcomframeset.asp', 'welcome.asp')

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

                committee.add_member(name, mtype)
