import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class VTCommitteeScraper(CommitteeScraper):
    state = 'vt'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        chamber_abbr = {'upper': 'S', 'lower': 'H'}[chamber]

        url = ('http://www.leg.state.vt.us/lms/legdir/comms.asp?Body=%s' %
               chamber_abbr)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for li in page.xpath("//li"):
                # Strip the room number from the committee name
                comm_name = re.match(r'[^\(]+', li.text).group(0).strip()

                # Strip chamber from beginning of committee name
                comm_name = re.sub(r'^(HOUSE|SENATE) COMMITTEE ON ', '',
                                   comm_name)

                comm_name = comm_name.title()

                comm = Committee(chamber, comm_name)
                comm.add_source(url)

                for tr in li.xpath("../../following-sibling::tr"):
                    # Break when we reach the next committee
                    if tr.xpath("th/li"):
                        break

                    name = tr.xpath("string()").strip()

                    match = re.search(
                        '^([\w\s\.]+),\s+'
                        '(Chair|Vice Chair|Ranking Member|Clerk)$',
                        name)
                    if match:
                        name = match.group(1)
                        mtype = match.group(2).lower()
                    else:
                        mtype = 'member'

                    name = re.sub(r'of [\w\s\.]+$', '', name)

                    comm.add_member(name, mtype)

                self.save_committee(comm)
