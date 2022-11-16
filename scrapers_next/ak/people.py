import re
import attr
from spatula import HtmlPage, HtmlListPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


def format_address(ad_str):
    whitespace_collapsed = re.sub(r"\s\s+", " ", ad_str)
    city_state_comma = re.sub(" AK", ", AK", whitespace_collapsed)
    addr_lines_comma = re.sub(r"(\d+) (\d+)", r"\1, \2", city_state_comma)
    return addr_lines_comma


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

        details = {
            "District": "",
            "Party": "",
            "Toll-Free": "",
            "Phone": "",
            "Fax": "",
        }

        for pattern in details.keys():
            pattern_match = re.search(rf"({pattern})(:\s+)(\S+)", div_text)
            if pattern_match:
                details[pattern] = pattern_match.groups()[-1]

        cap_ad_match = re.search(
            r"(State.+Room \d+)\s+(.+\s+AK,\s99801)(.+Contact)", div_text
        )
        if cap_ad_match:
            raw_session_contact = ", ".join(cap_ad_match.groups()[:2])
            session_contact = format_address(raw_session_contact)
            details["Capitol Address"] = session_contact

        dist_ad_match = re.search(
            r"(Interim Contact)\s+(\S+.+\S)\s\s+(.+99\d{3})", div_text
        )
        if dist_ad_match:
            raw_district_contact = ", ".join(dist_ad_match.groups()[1:])
            district_contact = format_address(raw_district_contact)
            details["District Address"] = district_contact

        dist_phone_match = re.search(r"(Interim.+Phone:)\s+(\S+)", div_text)
        if dist_phone_match:
            district_phone = dist_phone_match.groups()[1]
            details["District Phone"] = district_phone

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

        if details.get("District Phone"):
            p.district_office.voice = details["District Phone"]

        if details.get("Fax"):
            p.district_office.fax = details["Fax"]

        if details.get("District Address"):
            p.district_office.address = details["District Address"]
        p.district_office.name = "interim contact"

        if details.get("Capitol Address"):
            p.capitol_office.address = details["Capitol Address"]
        p.capitol_office.name = "session contact"

        if details.get("Toll-Free"):
            p.extras["toll_free_phone"] = details["Toll-Free"]

        source_url = str(self.source)
        p.add_source(source_url, "member detail page")

        session_match = re.search(r"(Detail/)(\d+)", source_url)
        session = session_match.groups()[1]
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
