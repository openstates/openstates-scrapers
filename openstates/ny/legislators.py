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
        url = "http://www.nysenate.gov/senators"
        page = self.urlopen(url)
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

            photo_link = link.xpath("../../../div[1]/span/a/img")[0]
            photo_url = photo_link.attrib['src']

            legislator = Legislator(term, 'upper', district,
                                    name, party="Unknown",
                                    photo_url=photo_url)
            legislator.add_source(url)

            contact_link = link.xpath("../span[@class = 'contact']/a")[0]
            contact_url = contact_link.attrib['href']
            self.scrape_upper_offices(legislator, contact_url)

            legislator['url'] = contact_url.replace('/contact', '')

            self.save_legislator(legislator)

    def scrape_upper_offices(self, legislator, url):
        page = self.urlopen(url)
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

        dist_str = page.xpath("string(//div[@class = 'district'])")
        match = re.findall(r'\(([A-Za-z,\s]+)\)', dist_str)
        if match:
            match = match[0].split(', ')
            party_map = {'D': 'Democratic', 'R': 'Republican',
                         'WF': 'Working Families',
                         'C': 'Conservative',
                         'IP': 'Independence',
                        }
            parties = [party_map.get(p.strip(), p.strip()) for p in match
                       if p.strip()]
            if 'Republican' in parties:
                party = 'Republican'
                parties.remove('Republican')
            elif 'Democratic' in parties:
                party = 'Democratic'
                parties.remove('Democratic')
            legislator['roles'][0]['party'] = party
            legislator['roles'][0]['other_parties'] = parties

        try:
            span = page.xpath("//span[. = 'Albany Office']/..")[0]
            address = span.xpath("string(div[1])").strip()
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
        page = self.urlopen(url)
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

        party_by_district = self._identify_lower_party()

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

            party = party_by_district[district]

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
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        try:
            contact = doc.xpath('//div[@id="addrinfo"]')[0]
        except:
            contact = doc
        email = None

        # Sometimes class is "addrcol1", others "addrcola"
        col_generators = [

            # Try alpha second.
            iter('abcedef'),

            # Try '' first, then digits.
            itertools.chain(iter(['']), iter(xrange(1, 5)))
            ]

        cols = col_generators.pop()
        while True:

            # Get the column value.
            try:
                col = cols.next()
            except StopIteration:
                try:
                    cols = col_generators.pop()
                except IndexError:
                    break
                else:
                    continue

            xpath = 'div[@class="addrcol%s"]' % str(col)
            address_data = contact.xpath(xpath)
            if not address_data:
                continue

            for data in address_data:
                data = (data.xpath('div[@class="officehdg"]/text()'),
                        data.xpath('div[@class="officeaddr"]/text()'))
                ((office_name,), address) = data

                if 'district' in office_name:
                    office_type = 'district'
                else:
                    office_type = 'capitol'

                # Phone can't be blank.
                phone = address.pop().strip()
                if not phone:
                    phone = None

                office = dict(
                    name=office_name, type=office_type, phone=phone,
                    fax=None, email=email,
                    address=''.join(address).strip())

                if not office['address']:
                    # Congrat's Maritza Davila, you have your own special
                    # exception in the code for people who have magical
                    # district offices with no mailing address.
                    # http://assembly.state.ny.us/mem/Maritza-Davila
                    continue

                legislator.add_office(**office)

    def _identify_lower_party(self):
        '''
        Get the best available information on NY State Assembly
        party affiliations. Returns a dict mapping district to party.
        '''

        # Download the page and ingest using lxml
        MEMBER_LIST_URL = \
                'http://www.elections.ny.gov:8080/reports/rwservlet?cmdkey=nysboe_incumbnt'
        html = self.urlopen(MEMBER_LIST_URL)
        doc = lxml.html.fromstring(html)

        # Map district to party affiliation
        party_affiliations = {}
        district = None
        party = None
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
                # Effectively reset the party affiliation tracking for each body
                # The State Assembly is the last one in the document, so only
                # they will be preserved
                if district == 1:
                    party_affiliations = {}
                capture_district = False
            elif capture_party:
                party_affiliations[district] = affiliation
                capture_party = False

            else:
                raise AssertionError(
                        "Assembly party parsing found inappropriate text: "
                        "'{}'".format(affiliation)
                        )

        return party_affiliations
