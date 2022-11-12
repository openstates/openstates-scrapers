import re
import attr
from spatula import HtmlPage, HtmlListPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


class PaginationError(Exception):
    pass


class PartyError(Exception):
    pass


class MissingAddress(Exception):
    pass


@attr.s(auto_attribs=True)
class PartialMember:
    image: str
    name: str
    chamber: str
    district: str
    party: str
    url: str
    start_date: str = ""


class LegDetail(HtmlPage):
    example_source = "https://www.ndlegis.gov/biography/mary-adams"

    def process_page(self):
        name_list = self.input.name.split()
        given_name = name_list[0]
        family_name_list = [x for x in name_list[1:] if "." not in x]
        family_name = re.sub(",", "", (" ".join(family_name_list)))

        if self.root.xpath(".//p[@class='address']"):
            address_span = CSS(".address").match(self.root)[0].text_content()
            address = ", ".join(address_span.split("\n")[:-1])
        else:
            address = ""

        node_content = CSS(".node__content").match(self.root)[0].text_content()
        contact_node = node_content.replace("\n", "").replace("\t", "")

        collected_contacts = {
            "Cell": "",
            "Fax": "",
            "Home": "",
            "Work": "",
            "Email": "",
        }

        for pattern in collected_contacts.keys():
            pattern_match = re.search(rf"({pattern}\s+)(\S+)", contact_node)
            if pattern_match:
                collected_contacts[pattern] = pattern_match.groups()[-1]

        p = ScrapePerson(
            name=self.input.name,
            given_name=given_name,
            family_name=family_name,
            state="nd",
            image=self.input.image,
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=collected_contacts["Email"],
        )

        p.district_office.address = address
        p.district_office.voice = collected_contacts["Work"]
        p.district_office.fax = collected_contacts["Fax"]

        for phone_type in ("Cell", "Home"):
            if collected_contacts.get(phone_type):
                p.extras[phone_type.lower()] = collected_contacts[phone_type]

        p.add_source(str(self.source), "member details page")

        members_list_url = str(self.input.url)
        p.add_source(members_list_url, "members list page")

        return p


class LegList(HtmlListPage):
    session = "67-2021"
    source = f"https://www.ndlegis.gov/assembly/{session}/regular/members"
    selector = XPath("//div[@class='member-wrapper']")
    next_page_selector = XPath(
        "//nav[@class='pager']/ul/li[@class='page-item pager__item--next']/a/@href"
    )

    def get_next_source(self):

        try:
            next_urls = self.next_page_selector.match(self.root)
        except SelectorError:
            return

        if len(set(next_urls)) > 1:
            raise PaginationError(
                f"get_next_source returned multiple links: {next_urls}"
            )

        return next_urls[0]

    def process_item(self, item):
        img_elem = item.find_class("image-style-member-list-photo")[0]
        img_src = img_elem.get("src")

        name_wrapper = item.find_class("strong member-name")[0]
        name_tag = name_wrapper.getchildren()[0]
        member_name = name_tag.text_content().strip()

        chamber_div = item.find_class("strong member-chamber")[0]
        chamber = chamber_div.text_content().strip()
        if chamber == "Senator":
            chamber = "upper"
        else:
            chamber = "lower"

        status = item.find_class("member-status")
        start_date = ""
        if status:
            status_text = status[0].text_content().strip()
            if "Expelled" in status_text:
                self.skip()
            elif "Active" in status_text:
                start_date = status_text.split()[-1].strip()

        district_div = item.find_class("district")[0].text_content().strip()
        district = re.search(r"(District\s+)(\S+)", district_div).groups()[-1]

        party_dict = {
            "D": "Democratic",
            "R": "Republican",
            "I": "Independent",
        }
        party_abbr = district_div[-1]
        if party_dict.get(party_abbr):
            party = party_dict[party_abbr]
        else:
            raise PartyError("Unknown political party encountered")

        details_source = name_tag.get("href")

        p = PartialMember(
            image=img_src,
            name=member_name,
            chamber=chamber,
            district=district,
            party=party,
            url=self.source.url,
            start_date=start_date,
        )

        return LegDetail(p, source=details_source)
