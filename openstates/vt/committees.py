import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

from .utils import DOUBLED_NAMES


class VTCommitteeScraper(CommitteeScraper):
    jurisdiction = 'vt'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        chamber_abbr = {'upper': 'S', 'lower': 'H'}[chamber]

        url = ('http://www.leg.state.vt.us/legdir/comms.cfm?Body=%s&Session=2014' %
               chamber_abbr)
        html = self.urlopen(url)
        page = lxml.html.fromstring(html)
        comm = None
        for tr in page.xpath('//table')[3].xpath('tr')[1:]:

            tds = list(tr)
            if len(tds) < 2:
                continue

            if 'COMMITTEE' in tds[1].text_content():
                # Save the current committee.
                if (comm or {}).get('members', []):
                    self.save_committee(comm)
                # Start a new one.
                comm = self.parse_committee_name(tds[1], chamber)
                comm.add_source(url)
                print comm
                continue

            name = tds[1].text_content().strip()
            match = re.search(
                '^([\w\s\.]+),\s+'
                '(Chair|Vice Chair|Vice-Chair|Ranking Member|Clerk)$',
                name)
            if match:
                name = match.group(1)
                mtype = match.group(2).lower()
            else:
                mtype = 'member'

            # if not name.startswith(DOUBLED_NAMES):
            name = re.sub(r'of [\w\s\.]+$', '', name)

            print name
            comm.add_member(name, mtype)


    def parse_committee_name(self, td, chamber):
        # Strip the room number from the committee name
        comm_name = re.match(r'[^\(]+', td.text_content()).group(0).strip()

        # Strip chamber from beginning of committee name
        comm_name = re.sub(r'^(HOUSE|SENATE) COMMITTEE ON ', '',
                           comm_name)
        # normalize case of committee name
        comm_name = comm_name.title()

        return Committee(chamber, comm_name)
