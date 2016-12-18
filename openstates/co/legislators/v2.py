"""
Colorado legislator scraper for http://leg.colorado.gov
"""

from ..utils.email import mailto_to_email
from ..utils.names import last_name_first_name_to_full_name

from openstates.utils import LXMLMixin

from billy.scrape.legislators import LegislatorScraper, Legislator


OPEN_STATES_CHAMBER_TO_CO_INTERNAL_CHAMBER_ID = {
    'upper': 1,
    'lower': 2,
}


class COLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'co'
    legislators_url = 'http://leg.colorado.gov/legislators'

    def scrape(self, chamber, term):
        """Scrape legislator information for the 2015-2016 term.

        The legislators page has an inactive dropdown to select the session.  When the dropdown is activated
        and we can see how it changes the page's query parameters, this scraper should be modified to filter to a
        session appropriate for the term.
        """
        co_internal_chamber_id = OPEN_STATES_CHAMBER_TO_CO_INTERNAL_CHAMBER_ID[chamber]
        # XXX: Filter by session when we find out the appropriate query params
        filtered_legislators_page_url = '{legislators_url}/?field_chamber_target_id={internal_chamber_id}'.format(
            legislators_url=self.legislators_url,
            internal_chamber_id=co_internal_chamber_id,
        )

        filtered_legislators_page = self.lxmlize(filtered_legislators_page_url)

        # '//table' is simple and safe. There is only one table on the legislator listings page, and it is unlikely
        # that more will be added.
        for row in filtered_legislators_page.xpath('//table//tr'):
            legislator, profile_url = table_row_to_legislator_and_profile_url(row, chamber, term)
            legislator_profile_page = self.lxmlize(profile_url)
            legislator['photo_url'] = get_photo_url(legislator_profile_page)
            office_kwargs = get_office_kwargs(legislator_profile_page)
            legislator.add_office('capitol', 'Capitol Office', **office_kwargs)
            legislator.add_source(self.legislators_url)
            legislator.add_source(profile_url)
            self.save_legislator(legislator)


# Helpers to extract from information from the main listings page
def table_row_to_legislator_and_profile_url(table_row_element, chamber, term):
    """Derive a Legislator from an HTML table row lxml Element, and a url for their more detailed profile page"""
    # Ignore title and phone number elements. We're getting phone from the details page and title is in the state
    # metadata
    (_, name_element, district_element, party_element, _) = table_row_element.xpath('td')
    # Name comes in the form Last, First
    last_name_first_name = name_element.text_content().strip()
    full_name = last_name_first_name_to_full_name(last_name_first_name)
    district = district_element.text_content().strip()
    party = party_element.text_content().strip()

    legislator = Legislator(term, chamber, district, full_name, party=party)

    (profile_url, ) = name_element.xpath('a/@href')

    return legislator, profile_url


# Helpers to extract information from each legislator's individual profile page
def get_photo_url(legislator_profile_page):
    """Scrape the URL of the photo used on the legislator profile page"""
    (photo_url, ) = legislator_profile_page.xpath(
        '//div[contains(@class, "legislator-profile-picture")]/descendant-or-self::img/@src'
    )

    return photo_url


def get_office_kwargs(legislator_profile_page):
    """Extract the kwargs to pass into `add_office` for the Legislator's office at the Capitol from the profile page"""
    (contact_information_container, ) = legislator_profile_page.xpath('//div[contains(@class, "legislator-contact")]')
    (address_element, ) = contact_information_container.xpath('div[contains(@class, "contact-address")]')
    (_, phone_element) = contact_information_container.xpath('div[contains(@class, "contact-phone")]/div/div')
    # Email address may or may not be present
    email_address_hrefs = contact_information_container.xpath('div[@class="contact-email"]/a/@href')

    address = address_from_profile_page_address_element(address_element)
    phone = phone_element.text_content().strip()
    if email_address_hrefs:
        (mailto_url, ) = email_address_hrefs
        email = mailto_to_email(mailto_url)
    else:
        email = None

    return {
        'address': address,
        'email': email,
        'phone': phone,
    }


def address_from_profile_page_address_element(address_element):
    """Extract a formatted address from the address container on the profile page"""
    # Address Line 1, e.g. 200 E Colfax
    (thoroughfare_element, ) = address_element.xpath('descendant-or-self::div[contains(@class, "thoroughfare")]')
    # Addres line 2, e.g RM 207
    (premise_element, ) = address_element.xpath('descendant-or-self::div[contains(@class, "premise")]')
    (locality_block, ) = address_element.xpath('descendant-or-self::div[contains(@class, "locality-block")]')
    # City, State Postal
    thoroughfare = thoroughfare_element.text_content().strip()
    premise = premise_element.text_content().strip()
    locality = locality_block.text_content().strip()

    return '{thoroughfare}\n{premise}\n{locality}'.format(
        thoroughfare=thoroughfare,
        premise=premise,
        locality=locality,
    )
