import re

from pupa.scrape import Scraper, Organization

import lxml.html

COMM_TYPES = {'joint': 'Joint',
              # 'task_force': 'Task Force',
              'upper': 'Senate',
              'lower': 'House'}


class ARCommitteeScraper(Scraper):
    jurisdiction = 'ar'
    latest_only = True

    _seen = set()

    def scrape(self, chamber=None):

        base_url = 'http://www.arkleg.state.ar.us/assembly/2017/2017R/Pages/Committees.aspx?committeetype='

        for chamber, url_ext in COMM_TYPES.items():
            chamber_url = base_url + url_ext
            page = self.get(chamber_url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(chamber_url)

            for a in page.xpath('//td[@class="dxtl dxtl__B0"]/a'):
                if a.attrib.get('colspan') == '2':
                    # colspan=2 signals a subcommittee, but it's easier
                    # to pick those up from links on the committee page,
                    # so we do that in scrape_committee() and skip
                    # it here
                    continue

                name = re.sub(r'\s*-\s*(SENATE|HOUSE)$', '', a.text).strip()

                comm_url = a.get('href').replace('../', '/')
                if chamber == 'task_force':
                    chamber = 'joint'

                yield from self.scrape_committee(chamber, name, comm_url)

    def _fix_committee_case(self, subcommittee):
        '''Properly capitalize the committee name.
        '''
        subcommittee = re.sub(
            r'^(HOUSE|SENATE|JOINT)\s+', '', subcommittee.strip().title())

        # Fix roman numeral capping.
        replacer = lambda m: m.group().upper()
        subcommittee = re.sub(
            r'\b(VII|VII|III|IIV|IV|II|VI|IX|V|X)\b', replacer, subcommittee,
            flags=re.I)
        return subcommittee

    def _fix_committee_name(self, committee, parent=None, subcommittee=False):
        '''Remove committee acronyms from committee names. We want to
        remove them from the beginning of names, and at the end:

        ARKANSAS LEGISLATIVE COUNCIL (ALC)
        ALC/EXECUTIVE SUBCOMMITTEE
        ALC-ADMINISTRATIVE RULES & REGULATIONS

        Also strip the main committee name from the committee.
        '''
        junk = ['ALC', 'ALC-JBC', 'JBC', 'JPR']

        if subcommittee:
            junk += [
                'AGING\s+&\s+LEGISLATIVE\s+AFFAIRS\s*-',
                'AGRICULTURE\s*-',
                'CITY, COUNTY & LOCAL AFFAIRS\s*-',
                'EDUCATION\s*-',
                'JUDICIARY\s*-',
                'PUBLIC HEALTH\s*-',
                'STATE AGENCIES & GOV. AFFAIRS\s*-',
                'TRANSPORTATION\s*-',
                ]

        if parent:
            junk += [parent]

        committee = committee.strip()
        for rgx in sorted(junk, key=len, reverse=True):
            match = re.match(rgx, committee, flags=re.I)
            if match:
                committee = committee.replace(match.group(), '', 1).strip()
                break

        # Kill "(ALC)" in "Blah Blah (ALC)"
        rgx = '\(?(%s)\)?' % '|'.join(sorted(junk, key=len, reverse=True))
        committee = re.sub(rgx, '', committee, flags=re.I)
        committee = committee.strip(' \/-\n\r\t')

        # Fix commas with no space.
        def replacer(matchobj):
            return matchobj.group(1) + ', ' + matchobj.group(2)
        rgx = r'(?i)([a-z]),([a-z])'
        committee = re.sub(rgx, replacer, committee)

        # Fix subcom.
        committee = committee.replace('Subcom.', 'Subcommittee')
        return committee

    def scrape_committee(self, chamber, name, url, subcommittee=None):
        name = self._fix_committee_name(name)
        name = self._fix_committee_case(name)

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # Get the subcommittee name.
        xpath = '//div[@class="ms-WPBody"]//table//tr/td/b/text()'

        if subcommittee:
            subcommittee = page.xpath(xpath)
            if subcommittee:
                subcommittee = page.xpath(xpath).pop(0)
                subcommittee = self._fix_committee_name(
                    subcommittee, parent=name, subcommittee=True)
                subcommittee = self._fix_committee_case(subcommittee)
            else:
                subcommittee = None

        # Dedupe.
        if (chamber, name, subcommittee) in self._seen:
            return
        self._seen.add((chamber, name, subcommittee))

        comm = Organization(chamber=chamber, name=name, classification='committee')
        comm.add_source(url)

        member_nodes = page.xpath('//table[@class="dxgvTable"]/tr')

        for member_node in member_nodes:
            # Skip empty rows.
            if member_node.attrib['class'] == 'dxgvEmptyDataRow':
                continue

            mtype = member_node.xpath('string(td[1])').strip()

            if not mtype:
                mtype = 'member'

            member = member_node.xpath('string(td[3])').split()

            member = ' '.join(member[1:])

            comm.add_member(member, role=mtype)

        for a in page.xpath('//table[@id="ctl00_m_g_a194465c_f092_46df_b753_'
                            '354150ac7dbd_ctl00_tblContainer"]//ul/li/a'):
            sub_name = a.text.strip()
            sub_url = a.get('href').replace('../', '/')
            self.scrape_committee(chamber, name, sub_url,
                                  subcommittee=sub_name)

        if not comm._related:
            if subcommittee:
                self.warning('Not saving empty subcommittee {}.'.format(
                    subcommittee))
            else:
                self.warning('Not saving empty committee {}.'.format(name))
        else:
            yield comm
