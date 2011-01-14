import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.committees import CommitteeScraper, Committee

import lxml.html


class UTCommitteeScraper(CommitteeScraper):
    state = 'ut'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        chamber_abbr = {'upper': 's', 'lower': 'h'}[chamber]

        url = "http://le.utah.gov/asp/interim/standing.asp?house=%s" % chamber_abbr
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for comm_link in page.xpath("//a[contains(@href, 'Com=')]"):
                comm_name = comm_link.text.strip()

                # Drop leading "House" or "Senate" from name
                comm_name = re.sub(r"^(House|Senate) ", "", comm_name)

                comm = Committee(chamber, comm_name)

                for mbr_link in comm_link.xpath(
                    "../../../font[2]/a[not(contains(@href, 'mailto'))]"):

                    name = mbr_link.text.strip()

                    next_el = mbr_link.getnext()
                    if next_el is not None and next_el.tag == 'i':
                        type = next_el.text.strip()
                    else:
                        type = 'member'

                    comm.add_member(name, type)

                self.save_committee(comm)


