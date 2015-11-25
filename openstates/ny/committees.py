# -*- coding: utf-8 -*-
import re
import lxml.html
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin


class NYCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = "ny"
    latest_only = True

    def _parse_name(self, name):
        """
        Split a committee membership string into name and role.

        >>> parse_name('Felix Ortiz')
        ('Felix Ortiz', 'member')
        >>> parse_name('Felix Ortiz (Chair)')
        ('Felix Ortiz', 'chair')
        >>> parse_name('Hon. Felix Ortiz, Co-Chair')
        ('Felix Ortiz', 'co-chair')
        >>> parse_name('Owen H.\\r\\nJohnson (Vice Chairperson)')
        ('Owen H. Johnson', 'vice chairperson')
        """
        name = re.sub(r'^(Hon\.|Assemblyman|Assemblywoman)\s+', '', name)
        name = re.sub(r'\s+', ' ', name)

        roles = ['Chairwoman', 'Chairperson', 'Chair', 'Secretary',
            'Treasurer', 'Parliamentarian', 'Chaplain']
        match = re.match(
            r'([^(]+),? \(?((Co|Vice)?-?\s*(%s))\)?' % '|'.join(roles),
            name)

        role = 'member'

        if match:
            name = match.group(1).strip(' ,')
            role = match.group(2).lower()

        name = name.replace('Sen.', '').replace('Rep.', '').strip()

        return (name, role)

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')()


    def scrape_lower_chamber(self, only_names=None):
        url = 'http://assembly.state.ny.us/comm/'

        page = self.lxmlize(url)

        committees = []

        link_nodes = self.get_nodes(
            page,
            '//a[contains(@href, "sec=mem")]')

        for link_node in link_nodes:
            committee_name_text = self.get_node(
                link_node,
                '../strong/text()')

            if committee_name_text is not None:
                committee_name = committee_name_text.strip()
                assert committee_name

                if 'Caucus' in committee_name:
                    continue

                committees.append(committee_name)

                url = link_node.attrib['href']
                committee = self.scrape_lower_committee(committee_name, url)

                self.save_committee(committee)

        return committees


    def scrape_lower_committee(self, name, url):
        page = self.lxmlize(url)

        committee = Committee('lower', name)
        committee.add_source(url)

        seen = set()

        member_links = self.get_nodes(
            page,
            '//div[@class="commlinks"]//a[contains(@href, "mem")]')

        for member_link in member_links:
            member_name = None
            member_role = None

            member_text = member_link.text
            if member_text is not None:
                member = member_text.strip()
                member = re.sub(r'\s+', ' ', member)
                member_name, member_role = self._parse_name(member)

            if member_name is None:
                continue

            # Figure out if this person is the chair.
            role_type = self.get_node(
                member_link,
                '../../preceding-sibling::div[1]/text()')

            if role_type in (['Chair'], ['Co-Chair']):
                member_role = 'chair'
            else:
                member_role = 'member'

            if name not in seen:
                committee.add_member(member_name, member_role)
                seen.add(member_name)

        return committee


    def scrape_upper_chamber(self):
        url = 'http://www.nysenate.gov/senators-committees'

        page = self.lxmlize(url)

        committees = []

        committee_nodes = self.get_nodes(
            page,
            '//div[@id="c-committees-container"][1]//'
            'a[@class="c-committee-link"]')

        for committee_node in committee_nodes:
            name_text = self.get_node(
                committee_node,
                './h4[@class="c-committee-title"][1]/text()')

            if name_text is not None:
                name = name_text.strip()
                assert name

                committees.append(name)

                # Retrieve committee information.
                committee_url = committee_node.attrib['href']
                committee = self.scrape_upper_committee(name,
                    committee_url)

                self.save_committee(committee)

        return committees


    def scrape_upper_committee(self, committee_name, url):
        page = self.lxmlize(url)

        committee = Committee('upper', committee_name)
        committee.add_source(url)

        # Committee member attributes.
        member_name = None
        member_role = None

        # Attempt to record the committee chair.
        committee_chair = self.get_node(
            page,
            '//div[@class="nys-senator" and div[@class="nys-senator--info"'
            ' and p[@class="nys-senator--title" and'
            ' normalize-space(text())="Chair"]]]')
        if committee_chair is not None:
            info_node = self.get_node(
                committee_chair,
                'div[@class="nys-senator--info" and p[@class='
                '"nys-senator--title" and contains(text(), "Chair")]]')
            if info_node is not None:
                # Attempt to retrieve committee chair's name.
                member_name_text = self.get_node(
                    info_node,
                    './h4[@class="nys-senator--name"][1]/a[1]/text()')

                if member_name_text is not None:
                    member_name = member_name_text.strip()
                else:
                    warning = ('Could not find the name of the chair for the'
                        ' {} committee')
                    self.logger.warning(warning.format(committee_name))

                # Attempt to retrieve committee chair's role (explicitly).
                member_role_text = self.get_node(
                    info_node,
                    './p[@class="nys-senator--title" and contains(text(), '
                    '"Chair")][1]/text()')

                if member_role_text is not None:
                    member_role = member_role_text.strip()
                else:
                    # This seems like a silly case, but could still be useful
                    # to check for.
                    warning = ('Could not find the role of the chair for the'
                        ' {} committee')
                    self.logger.warning(warning.format(committee_name))

                if member_name is not None and member_role is not None:
                    committee.add_member(member_name, member_role)
            else:
                warning = ('Could not find information for the chair of the'
                    ' {} committee.')
                self.logger.warning(warning.format(committee_name))
        else:
            warning = 'Missing chairperson for the {} committee.'
            self.logger.warning(warning.format(committee_name))

        # Get list of regular committee members.
        member_nodes = self.get_nodes(
            page,
            '//div[contains(concat(" ", @class, " "), '
            '" c-senators-container ")]//div[@class="view-content"]/'
            ' div/a')

        # Attempt to record each committee member.
        for member_node in member_nodes:
            member_name = None

            member_name_text = self.get_node(
                member_node,
                './/div[@class="nys-senator--info"][1]/h4[@class='
                '"nys-senator--name"][1]/text()')

            if member_name_text is not None:
                member_name = member_name_text.strip()
            
            if member_name is not None:
                committee.add_member(member_name, 'member')
            else:
                warning = ('Could not find the name of a member in the {}'
                    ' committee')
                self.logger.warning(warning.format(committee_name))

        return committee
