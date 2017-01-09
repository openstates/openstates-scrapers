from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin

base_url = 'http://www.nmlegis.gov/Committee/'


def clean_committee_name(name_to_clean):
    head, separator, tail = name_to_clean.replace('House ', '')\
        .replace('Senate ', '')\
        .replace('Subcommittee', 'Committee')\
        .rpartition(' Committee')

    return head + tail


class NMCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'nm'

    def scrape(self, chamber, term):
        self.validate_term(term)

        # Xpath query string format for legislative chamber committee urls
        base_xpath = (
            '//table[@id="MainContent_gridView{0}Committees"]//a'
            '[contains(@id, "MainContent_gridView{1}Committees_link'
            '{2}Committee")]/@href')

        if chamber == 'upper':
            url = '{}Senate_Standing'.format(base_url)
            chamber_xpath = base_xpath.format('Senate', 'Senate', 'Senate')

            # Most interim committees are joint. Use 'joint' chamber
            # as the way to collect Interim committee data
            self.scrape('joint', term)

        elif chamber == 'lower':
            url = '{}House_Standing'.format(base_url)
            chamber_xpath = base_xpath.format('House', 'House', 'House')

        elif chamber == 'joint':
            url = '{}Interim'.format(base_url)
            chamber_xpath = base_xpath.format('', '', '')

        page = self.lxmlize(url)

        committee_urls = self.get_nodes(page, chamber_xpath)

        for committee_url in committee_urls:
            self.scrape_committee(chamber, committee_url)

    def scrape_committee(self, chamber, url):

        committee_page = self.lxmlize(url)

        name_node = self.get_node(
            committee_page,
            '//table[@id="MainContent_formViewCommitteeInformation"]/tr//h3')

        c_name = (
            name_node.text_content().strip()
            if name_node is not None and name_node.text_content() else None)

        if c_name:
            committee = Committee(chamber, clean_committee_name(c_name))

            members_xpath = (
                '//table[@id="MainContent_formViewCommitteeInformation_grid'
                'ViewCommitteeMembers"]/tbody/tr'
            )
            members = self.get_nodes(committee_page, members_xpath)

            tds = {
                'title': 0,
                'name': 1,
                'role': 3
            }

            for member in members:
                m_title = member[tds['title']].text_content()
                m_name = self.get_node(
                    member[tds['name']],
                    './/a[contains(@href, "/Members/Legislator?SponCode=")]'
                ).text_content()

                role = member[tds['role']].text_content()

                if m_title == 'Senator':
                    m_chamber = 'upper'
                elif m_title == 'Representative':
                    m_chamber = 'lower'
                else:
                    m_chamber = None

                if role in ('Chair', 'Co-Chair', 'Vice Chair',
                            'Member', 'Advisory'):
                    if chamber == 'joint':
                        m_role = 'interim {}'.format(role.lower())
                    else:
                        m_role = role.lower()
                else:
                    m_role = None

                if m_role:
                    committee.add_member(m_name, m_role, chamber=m_chamber)

            if not committee['members']:
                self.warning(
                    'skipping blank committee {0} at {1}'.format(c_name, url))
            else:
                committee.add_source(url)
                # Interim committees are collected during the scraping
                # for joint committees, and most interim committees
                # have members from both chambers. However, a small
                # number of interim committees (right now, just 1) have
                # only members from one chamber, so the chamber is set
                # to their chamber instead of 'joint' for those
                # committees.
                if chamber == 'joint':
                    m_chambers = set(
                        [mem['chamber'] for mem in committee['members']])
                    if len(m_chambers) == 1:
                        committee['chamber'] = m_chambers.pop()

                self.save_committee(committee)

        else:
            self.warning('No legislative committee found at {}'.format(url))
