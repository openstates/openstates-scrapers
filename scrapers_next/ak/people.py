import re
import attr
from spatula import HtmlPage, HtmlListPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    example_source = "http://www.akleg.gov/basis/Member/Detail/32?code=BCH"

    def process_page(self):

        details_div = CSS(".bioright").match(self.root)[0]

        name_span = CSS(".formal_name").match(details_div)[0].text_content()
        name_list = name_span.split(" ")
        given_name = name_list[1]
        family_name = " ".join(name_list[2:])

        email = CSS("a").match(details_div)[0].text_content().strip()

        div_text = details_div.text_content().replace("\r\n", " ")

        details = {}

        detail_patterns = [
            "District",
            "Party",
            "Toll-Free",
            "Phone",
            "Fax",
        ]

        for pattern in detail_patterns:
            match = re.search(rf"{pattern}:\s\S+", div_text)
            if match:
                detail = div_text[match.start() + len(pattern) + 2 : match.end()]
                details[pattern] = detail

        address_patterns = [r"Interim.+99\d\d\d", r"Session.+99801"]
        for address_pattern in address_patterns:
            address_match = re.search(address_pattern, div_text)
            if address_match:
                detail_content = div_text[address_match.start() : address_match.end()]
                detail = " ".join(detail_content.split()[2:])
                details[address_pattern] = detail

        district_phone_pattern = r"Interim.+Phone:\s\S+"
        district_phone_match = re.search(district_phone_pattern, div_text)
        if district_phone_match:
            district_phone = div_text[
                district_phone_match.end() - 12 : district_phone_match.end()
            ]
            details[district_phone_pattern] = district_phone

        party_formatting = {
            "Democrat": "Democratic",
            "Republican": "Republican",
            "Not": "Independent",
        }
        listed_party = details["Party"]
        party = party_formatting[listed_party]

        image = CSS(".legpic").match_one(self.root).get("src")

        p = ScrapePerson(
            name=f"{given_name} {family_name}",
            given_name=given_name,
            family_name=family_name,
            state="ak",
            chamber=self.input.chamber,
            party=party,
            image=image,
            district=details["District"],
            email=email,
        )

        try:
            leadership_title = (
                CSS(".leadership_title").match(details_div)[0].text_content()
            )
            p.extras["title"] = leadership_title
        except SelectorError:
            pass

        if details.get("Phone"):
            p.capitol_office.voice = details["Phone"]

        if details.get(district_phone_pattern):
            p.district_office.voice = details[district_phone_pattern]

        if details.get("Fax"):
            p.district_office.fax = details["Fax"]

        if details.get(address_patterns[0]):
            p.district_office.address = details[address_patterns[0]]
        p.district_office.name = "interim contact"

        if details.get(address_patterns[1]):
            p.capitol_office.address = details[address_patterns[1]]
        p.capitol_office.name = "session contact"

        if details.get("Toll-Free"):
            p.extras["toll_free_phone"] = details["Toll-Free"]

        source_url = str(self.source)
        p.add_source(source_url, "member detail page")

        session_match = re.search(r"Detail/\d+", source_url)
        session = source_url[session_match.start() + 7 : session_match.end()]
        p.add_source(
            f"https://www.akleg.gov/basis/mbr_info.asp?session={session}",
            "member list page",
        )

        return p


class LegList(HtmlListPage):
    session_num = "32"
    source = f"https://www.akleg.gov/basis/mbr_info.asp?session={session_num}"
    selector = XPath("//html/body/div[2]/div/div/table//tr[position()>1]/td[1]/nobr/a")

    def process_item(self, item):
        title = item.text_content()
        title_list = title.strip().split(" ")
        chamber = title_list[0]

        if chamber == "Senator":
            chamber = "upper"
        elif chamber == "Representative":
            chamber = "lower"

        source = item.get("href")

        p = PartialMember(chamber=chamber, url=self.source.url)

        return LegDetail(p, source=source)
