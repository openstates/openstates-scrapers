from billy.scrape.legislators import Legislator, LegislatorScraper
from openstates.utils import LXMLMixin


class VTLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'vt'
    latest_only = True

    def scrape(self, term, chambers):
        # Identify all legislators to scrape
        SEARCH_URL = 'http://legislature.vermont.gov/people/search/2016'
        LEGISLATOR_ID_XPATH = \
                '//select[starts-with(@data-placeholder, "Select Legislator")]/option/@value'

        doc = self.lxmlize(SEARCH_URL)
        legislator_ids = doc.xpath(LEGISLATOR_ID_XPATH)
        legislator_ids.remove('0')

        for legislator_id in legislator_ids:
            self._scrape_legislator_page(term, legislator_id)

    def _scrape_legislator_page(self, term, legislator_id):
        # Load the legislator's homepage
        legislator_url = \
                'http://legislature.vermont.gov/people/single/2016/{}'.\
                format(legislator_id)
        doc = self.lxmlize(legislator_url)

        # Gather information on the legislator
        NULL_PHOTO_URL = \
                'http://legislature.vermont.gov/mysite/images/profile.png'
        (photo_url, ) = doc.xpath('//img[@class="profile-photo"]/@src')
        if photo_url == NULL_PHOTO_URL:
            photo_url = ''

        (name, ) = doc.xpath('//div/h1/text()')
        if name.startswith("Representative "):
            chamber = 'lower'
            name = name[len("Representative "): ]
        elif name.startswith("Senator "):
            chamber = 'upper'
            name = name[len("Senator "): ]
        else:
            raise AssertionError(
                    "Name indicates neither a senator nor a representative")

        (info, ) = doc.xpath('//dl[@class="summary-table profile-summary"]')
        district = info.xpath(
                './dt[text()="District"]/following-sibling::dd[1]/a/text()')[0]
        if district.endswith(" District"):
            district = district[ :(len(district) - len(" District"))]
        party = info.xpath(
                './dt[text()="Party"]/following-sibling::dd[1]/text()')[0]
        bio = info.xpath(
                './dt[text()="Biography"]/following-sibling::dd[1]/text()')[0]

        leg = Legislator(
                term=term, chamber=chamber, district=district, full_name=name,
                party=party, biography=bio, photo_url=photo_url
                )
        leg.add_source(legislator_url)
        
        # Identify their offices
        if info.xpath('./dt[text()="Email"]'):
            email = info.xpath(
                    './dt[text()="Email"]/following-sibling::dd[1]/a/text()')[0]
        else:
            email = None

        if info.xpath('./dt[text()="Home Address"]'):
            personal_address = info.xpath(
                    './dt[text()="Home Address"]/following-sibling::dd[1]/text()')[0]
        else:
            personal_address = None
        if info.xpath('./dt[text()="Home Phone"]'):
            personal_phone = info.xpath(
                    './dt[text()="Home Phone"]/following-sibling::dd[1]/text()')[0]
        else:
            personal_phone = None

        if info.xpath('./dt[text()="Work Address"]'):
            work_address = info.xpath(
                    './dt[text()="Work Address"]/following-sibling::dd[1]/text()')[0]
        else:
            work_address = None
        if info.xpath('./dt[text()="Work Phone"]'):
            work_phone = info.xpath(
                    './dt[text()="Work Phone"]/following-sibling::dd[1]/text()')[0]
        else:
            work_phone = None

        if personal_address and personal_phone:
            leg.add_office(
                    type='district', name='District Office',
                    address=personal_address, phone=personal_phone, email=email
                    )
        elif work_address and work_phone:
            leg.add_office(
                        type='district', name='District Office',
                        address=work_address, phone=work_phone, email=email
                        )
        elif (personal_address or personal_phone):
            leg.add_office(
                        type='district', name='District Office',
                        address=personal_address, phone=personal_phone,
                        email=email
                        )
        else:
            raise AssertionError(
                    "No address-phone information found for {}".format(name))

        # Capture their committee positions
        if info.xpath('./dt[text()="Committees"]'):
            committee_elements = info.xpath(
                    './dt[text()="Committees"]/following-sibling::dd[1]/ul/li//text()')
            self._scrape_committees(leg, committee_elements)

        # Save the legislator
        self.save_legislator(leg)

    def _scrape_committees(self, leg, committee_elements):
        name = ''
        for text in committee_elements:
            text = text.strip()

            if not text:
                pass

            elif text.startswith(", "):
                role = text[2: ]

            elif "Committee" in text or "Council" in text:
                # If there is already a committee scraped, save that one
                if name:
                    leg.add_role(
                            role='committee member',
                            term=leg['roles'][0]['term'],
                            chamber=chamber, committee=name, position=role
                            )

                role = 'member'
                name = text

                if text.startswith("House Committee "):
                    chamber = 'lower'
                elif text.startswith("Senate Committee "):
                    chamber = 'upper'
                else:
                    chamber = 'joint'
            else:
                raise AssertionError(
                        "Committee parsing found unexpected text: '{}'".\
                        format(text)
                        )

        if name:
            leg.add_role(
                    role='committee member', term=leg['roles'][0]['term'],
                    chamber=chamber, committee=name, position=role
                    )
