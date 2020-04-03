import re
from openstates_core.scrape import Person, Scraper
from openstates.utils import LXMLMixin

base_url = "http://www.nmlegis.gov/Members/Legislator_List"


def extract_phone_number(phone_number):
    phone_pattern = re.compile(r"(\(?\d{3}\)?\s?-?)?(\d{3}-?\d{4})")
    return phone_pattern.search(phone_number).groups()


class NMPersonScraper(Scraper, LXMLMixin):
    jurisdiction = "nm"

    def scrape(self, chamber=None):

        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        if chamber == "upper":
            query = "?T=S"
        else:
            query = "?T=R"

        self.logger.info("Scraping {} {} chamber.".format(self.jurisdiction, chamber))

        url = "{0}{1}".format(base_url, query)

        page = self.lxmlize(url)

        # Xpath query string format for legislator links.
        base_xpath = (
            "//a[contains(@id, "
            '"MainContent_listViewLegislators_linkLegislatorPicture")]/@href'
        )

        legislator_urls = self.get_nodes(page, base_xpath)

        for legislator_url in legislator_urls:
            if re.search(r"SponCode=[HS]VACA$", legislator_url, re.IGNORECASE):
                self.warning("Skipping vacant seat.")
                continue
            yield from self.scrape_legislator(chamber, legislator_url)

    def scrape_legislator(self, chamber, url):
        # Initialize default values for legislator attributes.
        full_name = None
        party = None
        photo_url = None
        email = None
        capitol_address = None
        capitol_phone = None
        district = None
        district_address = None
        district_phone = None

        if chamber == "upper":
            title_prefix = "Senator "
        elif chamber == "lower":
            title_prefix = "Representative "
        else:
            title_prefix = ""

        santa_fe_area_code = "(505)"

        page = self.lxmlize(url)

        info_node = self.get_node(page, '//table[@id="MainContent_formViewLegislator"]')
        if info_node is None:
            raise ValueError("Could not locate legislator data.")

        district_node = self.get_node(
            info_node, './/a[@id="MainContent_formViewLegislator_linkDistrict"]'
        )
        if district_node is not None:
            district = district_node.text.strip()

        name_node = self.get_node(
            page,
            './/span[@id="MainContent_formViewLegislatorName' '_lblLegislatorName"]',
        )

        if name_node is not None:
            if name_node.text.strip().endswith(" Vacant"):
                self.warning(
                    "Found vacant seat for {} district {}; skipping".format(
                        chamber, district
                    )
                )
                return

            n_head, _sep, n_party = name_node.text.rpartition(" - ")

            full_name = re.sub(r"^{}".format(title_prefix), "", n_head.strip())

            if "(D)" in n_party:
                party = "Democratic"
            elif "(R)" in n_party:
                party = "Republican"
            elif "(DTS)" in n_party:
                # decline to state = independent
                party = "Independent"
            else:
                raise AssertionError("Unknown party {} for {}".format(party, full_name))

        photo_node = self.get_node(
            info_node, './/img[@id="MainContent_formViewLegislator_imgLegislator"]'
        )
        if photo_node is not None:
            photo_url = photo_node.get("src")

        email_node = self.get_node(
            info_node, './/a[@id="MainContent_formViewLegislator_linkEmail"]'
        )
        if email_node is not None and email_node.text:
            email = email_node.text.strip()

        capitol_address_node = self.get_node(
            info_node, './/span[@id="MainContent_formViewLegislator_lblCapitolRoom"]'
        )
        if capitol_address_node is not None:
            capitol_address_text = capitol_address_node.text
            if capitol_address_text is not None:
                capitol_address = "Room {} State Capitol\nSanta Fe, NM 87501".format(
                    capitol_address_text.strip()
                )

        capitol_phone_node = self.get_node(
            info_node, './/span[@id="MainContent_formViewLegislator_lblCapitolPhone"]'
        )
        if capitol_phone_node is not None:
            capitol_phone_text = capitol_phone_node.text
            if capitol_phone_text:
                capitol_phone_text = capitol_phone_text.strip()
                area_code, phone = extract_phone_number(capitol_phone_text)
                if phone:
                    capitol_phone = "{} {}".format(
                        area_code.strip() if area_code else santa_fe_area_code, phone
                    )

        district_address_node = self.get_node(
            info_node, './/span[@id="MainContent_formViewLegislator_lblAddress"]'
        )
        if district_address_node is not None:
            district_address = "\n".join(district_address_node.xpath("text()"))

        office_phone_node = self.get_node(
            info_node, './/span[@id="MainContent_formViewLegislator_lblOfficePhone"]'
        )

        home_phone_node = self.get_node(
            info_node, './/span[@id="MainContent_formViewLegislator_lblHomePhone"]'
        )

        if office_phone_node is not None and office_phone_node.text:
            district_phone_text = office_phone_node.text
        elif home_phone_node is not None and home_phone_node.text:
            district_phone_text = home_phone_node.text
        else:
            district_phone_text = None
        if district_phone_text:
            d_area_code, d_phone = extract_phone_number(district_phone_text)
            district_phone = "{} {}".format(d_area_code.strip(), d_phone)

        person = Person(
            name=full_name,
            district=district,
            party=party,
            primary_org=chamber,
            image=photo_url,
        )
        if district_address:
            person.add_contact_detail(
                type="address", value=district_address, note="District Office"
            )
        if district_phone:
            person.add_contact_detail(
                type="voice", value=district_phone, note="District Office"
            )
        if capitol_address:
            person.add_contact_detail(
                type="address", value=capitol_address, note="Capitol Office"
            )
        if capitol_phone:
            person.add_contact_detail(
                type="voice", value=capitol_phone, note="Capitol Office"
            )
        if email:
            person.add_contact_detail(type="email", value=email, note="Capitol Office")

        person.add_link(url)
        person.add_source(url)

        yield person
