import re
from html.parser import HTMLParser

from pupa.scrape import Scraper, Person, Organization

from openstates.utils import LXMLMixin


class ALPersonScraper(Scraper, LXMLMixin):
    _base_url = 'http://www.legislature.state.al.us/aliswww/ISD/'
    _parties = {
        '(D)': 'Democratic',
        '(R)': 'Republican',
        '(I)': 'Independent',
    }

    def scrape(self, chamber=None):
        self.committees = {}
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)
        for committee in self.committees.values():
            yield committee

    def scrape_chamber(self, chamber):
        # the url for each rep is unfindable (by me)
        # and the parts needed to make it up do not appear in the html or js.
        # we can find basic information on the main rep page, and sponsor
        # info on a version of their indivdual page called using only their
        # sponsor ID (which we have to scrape from ALISON)
        # we can't get detailed information without another ID
        # which I have not been able to find.
        if chamber == 'upper':
            member_list_url = self._base_url + 'Senate/ALSenators.aspx'
            legislator_base_url = self._base_url + 'ALSenator.aspx'
        elif chamber == 'lower':
            member_list_url = self._base_url + 'House/ALRepresentatives.aspx'
            legislator_base_url = self._base_url + 'ALRepresentative.aspx'

        page = self.lxmlize(member_list_url)

        legislator_nodes = self.get_nodes(
            page,
            '//div[@class="container container-main"]/table/tr/td/input')

        legislator_url_template = legislator_base_url + '?OID_SPONSOR='\
            '{oid_sponsor}&OID_PERSON={oid_person}'

        html_parser = HTMLParser()

        for legislator_node in legislator_nodes:
            # Set identifiers internal to AlisonDB.
            # Have to do this to OID_SPONSOR because they don't know
            # how to HTML and I'm making links absolute out of convenience.
            try:
                oid_sponsor = legislator_node.attrib['longdesc'].split('/')[-1]
                oid_person = legislator_node.attrib['alt']
            except KeyError:
                continue

            legislator_url = legislator_url_template.format(
                oid_sponsor=oid_sponsor, oid_person=oid_person)

            legislator_page = self.lxmlize(legislator_url)

            name_text = self.get_node(
                legislator_page,
                '//span[@id="ContentPlaceHolder1_lblMember"]',
            ).text_content()

            # This just makes processing the text easier.
            name_text = name_text.lower()

            # Skip vacant seats.
            if 'vacant' in name_text:
                continue

            # Removes titles and nicknames.
            name = html_parser.unescape(
                re.sub(
                    r'(?i)(representative|senator|&quot.*&quot)', '', name_text
                ).strip().title()
            )

            # Assemble full name by reversing last name, first name format.
            name_parts = [x.strip() for x in name.split(',')]
            full_name = '{0} {1}'.format(name_parts[1], name_parts[0])

            info_node = self.get_node(
                legislator_page,
                '//div[@id="ContentPlaceHolder1_TabSenator_body"]//table')

            district_text = self.get_node(
                info_node,
                './tr[2]/td[2]'
            ).text_content()
            district_text = district_text.replace('&nbsp;', u'')

            if chamber == 'upper':
                district = district_text.replace('Senate District', '').strip()
            elif chamber == 'lower':
                district = district_text.replace('House District', '').strip()

            party_text = self.get_node(
                info_node,
                './tr[1]/td[2]'
            ).text_content()

            if not full_name.strip() and party_text == '()':
                self.warning('Found empty seat, for district {}; skipping'.format(district))
                continue

            if party_text.strip() in self._parties.keys():
                party = self._parties[party_text.strip()]
            else:
                party = None

            phone_number = self.get_node(
                info_node,
                './tr[4]/td[2]'
            ).text_content().strip()

            fax_number = self.get_node(
                info_node,
                './tr[5]/td[2]',
            ).text_content().strip().replace('\u00a0', '')

            suite_text = self.get_node(
                info_node,
                './tr[7]/td[2]',
            ).text_content()

            office_address = '{}\n11 S. Union Street\nMontgomery, AL 36130'\
                .format(suite_text)

            email_address = self.get_node(
                info_node,
                './tr[11]/td[2]',
            ).text_content()

            photo_url = self.get_node(
                legislator_page,
                '//input[@id="ContentPlaceHolder1_TabSenator_TabLeg_imgLEG"]'
                '/@src')

            # add basic leg info and main office
            person = Person(
                name=full_name,
                district=district,
                primary_org=chamber,
                party=party,
                image=photo_url,
            )

            person.add_contact_detail(type='address', value=office_address, note='Capitol Office')
            if phone_number:
                person.add_contact_detail(type='voice', value=phone_number, note='Capitol Office')
            if fax_number:
                person.add_contact_detail(type='fax', value=fax_number, note='Capitol Office')
            if email_address:
                person.add_contact_detail(type='email', value=email_address, note='Capitol Office')

            self.add_committees(legislator_page, person, chamber, legislator_url)

            person.add_link(legislator_url)
            person.add_source(legislator_url)
            person.add_source(member_list_url)

            yield person

    def add_committees(self, legislator_page, legislator, chamber, url):
        # as of today, both chambers do committees the same way! Yay!
        rows = self.get_nodes(
            legislator_page,
            '//div[@id="ContentPlaceHolder1_TabSenator_TabCommittees"]//table/'
            'tr')

        if len(rows) == 0:
            return

        for row in rows[1:]:
            committee_name_text = self.get_node(row, './td[2]').text_content()
            committee_name = committee_name_text.strip()

            if not committee_name:
                continue

            role_text = self.get_node(row, './td[3]').text_content()
            role = role_text.strip()

            if committee_name not in self.committees:
                comm = Organization(
                    name=committee_name, chamber=chamber, classification='committee')
                comm.add_source(url)
                self.committees[committee_name] = comm

            self.committees[committee_name].add_member(
                legislator.name,
                role=role,
            )
