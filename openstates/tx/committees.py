import re

from pupa.scrape import Scraper, Organization

from openstates.utils import LXMLMixin


class TXCommitteeScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        committee_list_urls = {
            'lower': 'https://capitol.texas.gov/Committees/'
                     'CommitteesMbrs.aspx?Chamber=H',
            'upper': 'https://capitol.texas.gov/Committees/'
                     'CommitteesMbrs.aspx?Chamber=S'
        }

        committee_list_url = committee_list_urls[chamber]
        committee_list_page = self.lxmlize(committee_list_url)

        committee_nodes = self.get_nodes(
            committee_list_page,
            '//form[@id="ctl00"]//a[@id="CmteList"]'
        )

        for committee_node in committee_nodes:
            committee_name = committee_node.text.strip()
            committee = Organization(
                name=committee_name,
                chamber=chamber,
                classification='committee'
            )

            # Get the committee profile page.
            committee_page_url = committee_node.get('href')
            committee_page = self.lxmlize(committee_page_url)

            # Capture table with committee membership data.
            details_table = self.get_node(
                committee_page,
                '//div[@id="content"]//table[2]'
            )
            if details_table is not None:
                # Skip the first row because it currently contains only headers
                detail_rows = self.get_nodes(details_table, './tr')[1:]
                for detail_row in detail_rows:
                    label_text = self.get_node(detail_row, './td[1]//text()')

                    if label_text:
                        label_text = label_text.strip().rstrip(':')

                    if label_text in ('Chair', 'Vice Chair'):
                        member_role = 'chair'
                    else:
                        member_role = 'member'

                    member_name_text = self.get_node(
                        detail_row,
                        './td[2]/a/text()'
                    )

                    # Clean titles from member names.
                    if chamber == 'upper':
                        member_name = re.sub(r'^Sen\.[\s]*', '',
                                             member_name_text)
                    elif chamber == 'lower':
                        member_name = re.sub(r'^Rep\.[\s]*', '',
                                             member_name_text)

                    # Collapse multiple whitespaces in member names.
                    member_name = re.sub(r'[\s]{2,}', ' ', member_name).strip()

                    committee.add_member(member_name, member_role)

            committee.add_source(committee_list_url)
            committee.add_source(committee_page_url)

            yield committee
