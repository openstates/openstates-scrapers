import re
import HTMLParser
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class ALLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'al'

    _base_url = 'http://www.legislature.state.al.us/aliswww/ISD/'
    _parties = {
        '(D)': 'Democratic',
        '(R)': 'Republican', 
        '(I)': 'Independent',
    }

    def scrape(self, chamber, term):
        #the url for each rep is unfindable (by me)
        #and the parts needed to make it up do not appear in the html or js.
        #we can find basic information on the main rep page, and sponsor
        #info on a version of their indivdual page called using only their
        #sponsor ID (which we have to scrape from ALISON)
        #we can't get detailed information without another ID
        #which I have not been able to find.

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

        html_parser = HTMLParser.HTMLParser()

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
                '//span[@id="ContentPlaceHolder1_lblMember"]').text_content()\
                .encode('utf-8')

            # This just makes processing the text easier.
            name_text = name_text.lower()

            # Skip vacant seats.
            if 'vacant' in name_text:
                continue

            # Removes titles and nicknames.
            name = html_parser.unescape(re.sub(r'(?i)(representative|senator|'
                '&quot.*&quot)', '', name_text).strip().title())

            # Assemble full name by reversing last name, first name format.
            name_parts = [x.strip() for x in name.split(',')]
            full_name = '{0} {1}'.format(name_parts[1], name_parts[0])

            info_node = self.get_node(
                legislator_page,
                '//div[@id="ContentPlaceHolder1_TabSenator_body"]//table')

            party_text = self.get_node(
                info_node,
                './tr[1]/td[2]').text_content().encode('utf-8')

            party = self._parties[party_text.strip()]

            district_text = self.get_node(
                info_node,
                './tr[2]/td[2]').text_content().encode('utf-8')

            if chamber == 'upper':
                district = district_text.replace('Senate District', '').strip()
            elif chamber == 'lower':
                district = district_text.replace('House District', '').strip()

            phone_number_text = self.get_node(
                info_node,
                './tr[4]/td[2]').text_content().encode('utf-8')

            phone_number = phone_number_text.strip()

            fax_number_text = self.get_node(
                info_node,
                './tr[5]/td[2]').text_content().encode('utf-8')

            fax_number = fax_number_text.strip()

            suite_text = self.get_node(
                info_node,
                './tr[7]/td[2]').text_content().encode('utf-8')

            office_address = '{}\n11 S. Union Street\nMontgomery, AL 36130'\
                .format(suite_text)

            email_text = self.get_node(
                info_node,
                './tr[11]/td[2]').text_content().encode('utf-8')

            email_address = email_text.strip()

            photo_url = self.get_node(
                legislator_page,
                '//input[@id="ContentPlaceHolder1_TabSenator_TabLeg_imgLEG"]'
                '/@src')

            #add basic leg info and main office
            legislator = Legislator(
                term=term,
                district=district,
                chamber=chamber,
                full_name=full_name,
                party=party,
                email=email_address,
                photo_url=photo_url)

            legislator.add_office(
                'capitol',
                'Capitol Office',
                address=office_address,
                phone=phone_number)

            #match rep to sponsor_id if possible
            ln,fn = name.split(',')
            last_fi_key = '{ln} ({fi})'.format(ln=ln.strip(), fi=fn.strip()[0])

            if not oid_sponsor:
                #can't find rep's sponsor_id, do what we can and get out!
                self.logger.warning("Legislator {name} does not match any sponsor_id and thus will not be linked to bills or committees".format(name=rep_name))
                self.save_legislator(leg)
                continue

            self.add_committees(legislator_page, legislator, chamber, term)

            legislator.add_source(member_list_url)
            legislator.add_source(legislator_url)

            self.save_legislator(legislator)


    def add_committees(self, legislator_page, legislator, chamber, term):
        #as of today, both chambers do committees the same way! Yay!
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
            
            legislator.add_role('committee member',
                term=term,
                chamber=chamber,
                committee=committee_name,
                position=role)
