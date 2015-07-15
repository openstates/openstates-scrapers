# -*- coding: utf-8 -*-
import re
import itertools
import datetime

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html



class NYLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ny'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper(term)
        else:
            self.scrape_lower(term)

    def scrape_upper(self, term):
        party_by_district = self._identify_party('upper')

        url = "http://www.nysenate.gov/senators"
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = (
            '//div[contains(@class, "views-row")]/'
            'div[contains(@class, "last-name")]/'
            'span[contains(@class, "field-content")]/a')
        for link in page.xpath(xpath):
            if link.text in (None, 'Contact', 'RSS'):
                continue
            name = link.text.strip()
            if name.lower().startswith('senate district'):
                continue

            district = link.xpath("string(../../../div[3]/span[1])")
            district = re.match(r"District (\d+)", district).group(1)

            party = party_by_district[district].strip()

            photo_link = link.xpath("../../../div[1]/span/a/img")[0]
            photo_url = photo_link.attrib['src']

            legislator = Legislator(term, 'upper', district,
                                    name, party=party,
                                    photo_url=photo_url)
            legislator.add_source(url)

            contact_link = link.xpath("../span[@class = 'contact']/a")[0]
            contact_url = contact_link.attrib['href']
            self.scrape_upper_offices(legislator, contact_url)

            legislator['url'] = contact_url.replace('/contact', '')

            self.save_legislator(legislator)

    def scrape_upper_offices(self, legislator, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        legislator.add_source(url)

        xpath = '//a[contains(@href, "profile-pictures")]/@href'
        legislator['photo_url'] = page.xpath(xpath).pop()

        email = page.xpath('//span[@class="spamspan"]')
        if email:
            email = email[0].text_content()
            email = email.replace(' [at] ', '@').replace(' [dot] ', '.')
            legislator['email'] = email

        try:
            span = page.xpath("//span[. = 'Albany Office']/..")[0]
            address = span.xpath("string(div[1])").strip()
            address = re.sub(r'[ ]{2,}', "", address)
            address += "\nAlbany, NY 12247"

            phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
            phone = phone.text.strip()

            office = dict(
                    name='Capitol Office',
                    type='capitol', phone=phone,
                    fax=None, email=None,
                    address=address)
            legislator.add_office(**office)

        except IndexError:
            # Sometimes contact pages are just plain broken
            pass

        try:
            span = page.xpath("//span[. = 'District Office']/..")[0]
            address = span.xpath("string(div[1])").strip() + "\n"
            address += span.xpath(
                "string(span[@class='locality'])").strip() + ", "
            address += span.xpath(
                "string(span[@class='region'])").strip() + " "
            address += span.xpath(
                "string(span[@class='postal-code'])").strip()
            address = re.sub(r'[ ]{2,}', "", address)

            phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
            phone = phone.text.strip()

            office = dict(
                    name='District Office',
                    type='district', phone=phone,
                    fax=None, email=None,
                    address=address)

            legislator.add_office(**office)
        except IndexError:
            # No district office yet?
            pass

    def scrape_lower(self, term):
        url = "http://assembly.state.ny.us/mem/?sh=email"
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        # full_names = []

        def _split_list_on_tag(lis, tag):
            data = []
            for entry in lis:
                if entry.attrib['class'] == tag:
                    yield data
                    data = []
                else:
                    data.append(entry)

        party_by_district = self._identify_party('lower')

        for row in _split_list_on_tag(page.xpath(
                "//div[@id='maincontainer']/div[contains(@class, 'email')]"),
                "emailclear"
                ):

            try:
                name, district, email = row
            except ValueError:
                name, district = row
                email = None

            link = name.xpath(".//a[contains(@href, '/mem/')]")
            if link != []:
                link = link[0]
            else:
                link = None

            if email is not None:
            # XXX: Missing email from a record on the page
            # as of 12/11/12. -- PRT
                email = email.xpath(".//a[contains(@href, 'mailto')]")
                if email != []:
                    email = email[0]
                else:
                    email = None

            name = link.text.strip()
            if name == 'Assembly Members':
                continue

            # empty seats
            if 'Assembly District' in name:
                continue

            district = link.xpath("string(../following-sibling::"
                                  "div[@class = 'email2'][1])")
            district = district.rstrip('rthnds')

            party = party_by_district[district].strip()

            photo_url = "http://assembly.state.ny.us/mem/pic/%03d.jpg" % \
                    int(district)
            leg_url = link.get('href')
            
            legislator = Legislator(term, 'lower', district, name,
                                    party=party,
                                    url=leg_url,
                                    photo_url=photo_url)
            legislator.add_source(url)

            # Legislator
            self.scrape_lower_offices(leg_url, legislator)

            if email is not None:
                email = email.text_content().strip()
                if email:
                    legislator['email'] = email

            self.save_legislator(legislator)

    def scrape_lower_offices(self, url, legislator):
        legislator.add_source(url)

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for data in doc.xpath('//div[@class="officehdg"]'):
            data = (data.xpath('text()'),
                    data.xpath('following-sibling::div[1]/text()'))
            ((office_name,), address) = data

            if 'district' in office_name.lower():
                office_type = 'district'
            else:
                office_type = 'capitol'

            address = [x.strip() for x in address if x.strip()]

            fax = None
            if address[-1].startswith("Fax: "):
                fax = address.pop().replace("Fax: ", "")

            phone = None
            if re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}', address[-1]):
                phone = address.pop()

            address = '\n'.join(address)

            legislator.add_office(
                    name=office_name,
                    type=office_type,
                    phone=phone,
                    fax=fax,
                    address=address
                    )

    def _identify_party(self, chamber):
        '''
        Get the best available information on New York political party
        affiliations. Returns a dict mapping district to party for the
        given chamber.

        The formatting of this page is pretty abysmal, so apologies
        about the dirtiness of this method.
        '''

        # These may need to be changed, but should be mostly constant
        NY_SEATS_IN_US_HOUSE = 27
        NY_STATE_SENATE_SEATS = 63
        NY_STATE_ASSEMBLY_SEATS = 150

        # Download the page and ingest using lxml
        MEMBER_LIST_URL = \
                'http://www.elections.ny.gov:8080/reports/rwservlet?cmdkey=nysboe_incumbnt'
        html = self.get(MEMBER_LIST_URL).text
        doc = lxml.html.fromstring(html)

        # Map district to party affiliation
        _congressional_affiliations = {}
        senate_affiliations = {}
        assembly_affiliations = {}
        district = None
        capture_district = False
        capture_party = False
        affiliation_text = \
                doc.xpath('/html/body/table/tr/td/font[@color="#0000ff"]/b/text()')
        for affiliation in affiliation_text:

            if capture_district and capture_party:
                raise AssertionError(
                        "Assembly party parsing simultaneously looking for "
                        "both district number and party name"
                        )
            
            # Remove non-breaking space characters
            affiliation = re.sub("\xa0", " ", affiliation)

            # Ignore the header text when parsing
            try:
                datetime.datetime.strptime(affiliation, "%B %d, %Y")
                is_date = True
            except ValueError:
                is_date = False
            if is_date or \
                    affiliation == "Elected Representatives for New York State by Office and District":
                pass

            # Otherwise, check to see if a District or Party is indicated
            elif affiliation == u'District : ':
                capture_district = True
            elif affiliation == u'Party : ':
                capture_party = True

            # If a search has been initiated for District or Party, then capture them
            elif capture_district:
                district = affiliation
                assert district, "No district found"
                capture_district = False
            elif capture_party:
                # Skip capturing of members who are at-large, such as governor
                if not district:
                    capture_party = False
                    continue

                assert affiliation, "No party is indicated for district {}".format(district)

                # Congressional districts are listed first, then state
                # senate, then assembly
                # If a repeat district is seen, assume it's from the
                # next body in that list
                if (not _congressional_affiliations.get(district) and 
                        int(district) <= NY_SEATS_IN_US_HOUSE):
                    _congressional_affiliations[district] = affiliation.title()
                elif (not senate_affiliations.get(district) and 
                        int(district) <= NY_STATE_SENATE_SEATS):
                    senate_affiliations[district] = affiliation.title()
                elif (not assembly_affiliations.get(district) and
                        int(district) <= NY_STATE_ASSEMBLY_SEATS):
                    assembly_affiliations[district] = affiliation.title()
                else:
                    raise AssertionError(
                            "District {} appears too many times in party document".
                            format(district)
                            )

                district = None
                capture_party = False

            else:
                raise AssertionError(
                        "Assembly party parsing found inappropriate text: "
                        "'{}'".format(affiliation)
                        )

        if chamber == 'upper':
            return senate_affiliations
        elif chamber == 'lower':
            return assembly_affiliations
        else:
            raise AssertionError("Unknown chamber passed to party parser")
