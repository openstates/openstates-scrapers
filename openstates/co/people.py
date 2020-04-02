from openstates_core.scrape import Person, Scraper
from openstates.utils import LXMLMixin

CHAMBER_TO_CO_INTERNAL_CHAMBER_ID = {"lower": 1, "upper": 2}
UPPER_ROLE = "Senator"
UPPER_ADDRESS = "200 E. Colfax\nRM 346\nDenver, CO 80203"
LOWER_ROLE = "Representative"
LOWER_ADDRESS = "200 E. Colfax\nRM 307\nDenver, CO 80203"
ROLE_TO_ADDRESS = {UPPER_ROLE: UPPER_ADDRESS, LOWER_ROLE: LOWER_ADDRESS}


class COLegislatorScraper(Scraper, LXMLMixin):
    legislators_url = "http://leg.colorado.gov/legislators"

    def scrape(self, chamber=None):
        """Scrape legislator information for the 2015-2016 term.

        The legislators page has an inactive dropdown to select the session.
        When the dropdown is activated and we can see how it changes the
        page's query parameters, this scraper should be modified to
        filter to a session appropriate for the term.
        """
        if chamber:
            co_internal_chamber_ids = [CHAMBER_TO_CO_INTERNAL_CHAMBER_ID[chamber]]
        else:
            co_internal_chamber_ids = [
                CHAMBER_TO_CO_INTERNAL_CHAMBER_ID["lower"],
                CHAMBER_TO_CO_INTERNAL_CHAMBER_ID["upper"],
            ]
        # TODO: Filter by session when we find out the appropriate query params
        for co_internal_chamber_id in co_internal_chamber_ids:
            chamber = (
                "upper"
                if co_internal_chamber_id == CHAMBER_TO_CO_INTERNAL_CHAMBER_ID["upper"]
                else "lower"
            )
            filtered_legislators_page_url = "{legislators_url}/?field_chamber_target_id={internal_chamber_id}".format(
                legislators_url=self.legislators_url,
                internal_chamber_id=co_internal_chamber_id,
            )

            filtered_legislators_page = self.lxmlize(filtered_legislators_page_url)

            # '//table' is simple and safe. There is only one table on the legislator listings page
            # and it is unlikely that more will be added.
            for row in filtered_legislators_page.xpath("//table//tr"):
                legislator, profile_url = table_row_to_legislator_and_profile_url(
                    row, chamber
                )
                legislator_profile_page = self.lxmlize(profile_url)
                legislator.image = get_photo_url(legislator_profile_page)
                legislator.add_source(profile_url)
                legislator.add_source(self.legislators_url)
                legislator.add_link(profile_url)
                yield legislator


def co_address_from_role(role):
    """
    Translate the role to a legislative body (upper/lower) and return the
    address for that body
    """
    if role in ROLE_TO_ADDRESS:
        return ROLE_TO_ADDRESS[role]
    raise ValueError('Unknown role "{}"'.format(role))


# Helpers to extract from information from the main listings page
def table_row_to_legislator_and_profile_url(table_row_element, chamber):
    """Derive a Legislator from an HTML table row lxml Element, and a link to their profile"""
    td_elements = table_row_element.xpath("td")
    (
        role_element,
        name_element,
        district_element,
        party_element,
        phone_element,
        email_element,
    ) = td_elements

    # Name comes in the form Last, First
    # last_name_first_name = name_element.text_content().strip()
    # full_name = last_name_first_name_to_full_name(last_name_first_name)
    full_name = name_element.text_content().strip()
    if full_name.count(", ") == 1:
        full_name = " ".join(full_name.split(", ")[::-1]).strip()
    district = district_element.text_content().strip()
    party = party_element.text_content().strip()
    if party == "Democrat":
        party = "Democratic"
    elif party == "Unaffiliated":
        party = "Independent"

    role = role_element.text_content().strip()
    address = co_address_from_role(role)
    phone = phone_element.text_content().strip()
    email = email_element.text_content().strip()

    (profile_url,) = name_element.xpath("a/@href")
    print(chamber, district, party)
    legislator = Person(
        primary_org=chamber, name=full_name, district=district, party=party
    )
    legislator.add_contact_detail(type="address", value=address, note="Capitol Office")
    if phone:
        legislator.add_contact_detail(type="voice", value=phone, note="Capitol Office")
    if email:
        legislator.add_contact_detail(type="email", value=email, note="Capitol Office")

    return legislator, profile_url


# Helpers to extract information from each legislator's individual profile page
def get_photo_url(legislator_profile_page):
    """Scrape the URL of the photo used on the legislator profile page"""
    (photo_url,) = legislator_profile_page.xpath(
        '//div[contains(@class, "legislator-profile-picture")]/descendant-or-self::img/@src'
    )

    return photo_url
