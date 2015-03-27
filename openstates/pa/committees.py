import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class CommitteeDict(dict):

    def __missing__(self, key):
        (chamber, committee_name, subcommittee_name) = key
        committee = Committee(chamber, committee_name)
        if subcommittee_name:
            committee['subcommittee'] = subcommittee_name
        self[key] = committee
        return committee


class PACommitteeScraper(CommitteeScraper):
    jurisdiction = 'pa'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            url = ('http://www.legis.state.pa.us/cfdocs/legis/'
                   'home/member_information/senators_ca.cfm')
        else:
            url = ('http://www.legis.state.pa.us/cfdocs/legis/'
                   'home/member_information/representatives_ca.cfm')

        page = self.get(url).text
        page = lxml.html.fromstring(page)

        committees = CommitteeDict()

        for div in page.xpath("//div[@class='MemberInfoCteeList-Member']"):
            thumbnail, bio, committee_list, _ = list(div)
            name = bio.xpath(".//a")[-1].text_content().strip()
            namey_bits = name.split()
            party = namey_bits.pop().strip('()')
            name = ' '.join(namey_bits).replace(' ,', ',')

            for li in committee_list.xpath('div/ul/li'):

                # Add the ex-officio members to all committees, apparently.
                msg = 'Member ex-officio of all Standing Committees'
                if li.text_content() == msg:
                    for (_chamber, _, _), committee in committees.items():
                        if chamber != _chamber:
                            continue
                        committee.add_member(name, 'member')
                    continue

                # Everybody else normal.
                subcommittee_name = None
                committee_name = li.xpath('a/text()').pop()
                role = 'member'
                for _role in li.xpath('i/text()') or []:
                    if 'subcommittee' in _role.lower():
                        subcommittee_name, _, _role = _role.rpartition('-')
                        subcommittee_name = re.sub(r'[\s,]+', ' ',
                                                   subcommittee_name).strip()
                    role = re.sub(r'[\s,]+', ' ', _role).lower()

                # Add the committee member.
                key = (chamber, committee_name, subcommittee_name)
                committees[key].add_member(name, role)

        # Save the non-empty committees.
        for committee in committees.values():
            if not committee['members']:
                continue
            committee.add_source(url)
            self.save_committee(committee)
