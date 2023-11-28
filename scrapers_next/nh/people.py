import io
import csv
from spatula import URL, CsvListPage, HtmlPage, CSS
from openstates.models import ScrapePerson
import re
import requests
import lxml.html

# Regex compile for isolating variety of address formats on house detail pages
addr_w_zip_re = re.compile(r"(.+)\s+(03\d{3})")


def scrape_house_vals(url):
    """
    Helper function makes request of url for NH House members roster,
    gets the unique value needed for path to member's detail page,
    and stores each value under the key of member's name in collection.

    Example:
        {"Abare, Kimberly": "10621"}

    This function is called at initialization of Legislators object
    so the dictionary collection can be accessed to construct url for
    scraping each NH House member's detail page in HouseDetail.
    """
    response = requests.get(url)
    content = lxml.html.fromstring(response.content)
    dropdown_list = content.xpath(".//select[@name='ctl00$pageBody$ddlReps']//option")
    member_values = {}
    for option in dropdown_list:
        value = option.get("value")
        name = option.text_content().strip()
        member_values[name] = value
    return member_values


# TODO: Check member pages in future sessions for additional desirable data
#  not present in CSV List Page. If found, add such data processing to
#  SenateDetail and HouseDetail classes
class SenateDetail(HtmlPage):
    example_source = (
        "http://www.gencourt.state.nh.us/Senate/members/webpages/district22.aspx"
    )

    def process_page(self):
        p = self.input
        img = CSS("img.rounded").match_one(self.root).get("src")
        p.image = img
        return p


class HouseDetail(HtmlPage):
    example_source = (
        "http://www.gencourt.state.nh.us/house/members/member.aspx?pid=10621"
    )

    def process_page(self):
        p = self.input
        img = self.root.xpath(".//img[@id='pageBody_imgMember']")[0].get("src")
        if "nophoto" in img:
            img = ""
        p.image = img

        # A few house members don't have address listed in CSV List Page
        #  but DO have it listed on their member detail page
        if not p.district_office.address:
            contact = (
                self.root.xpath(".//p[@class='card-text']")[0].text_content().strip()
            )
            # Non-present addresses have only comma character listed on page
            if not contact[0] == ",":
                contact_parts = [x.strip() for x in contact.split("\r\n") if len(x)]
                address_lines = ", ".join(contact_parts[0:2])
                addr_match = addr_w_zip_re.search(address_lines)
                if addr_match:
                    addr = "".join(addr_match.groups())
                    p.district_office.address = addr
        return p


class Legislators(CsvListPage):
    def postprocess_response(self) -> None:
        self.reader = csv.DictReader(io.StringIO(self.response.text), delimiter="\t")

    source = URL("http://gencourt.state.nh.us/downloads/members.txt")

    house_url_vals = scrape_house_vals("http://www.gencourt.state.nh.us/house/members/")

    def process_item(self, item):
        last_name = item["LastName"].strip()
        first_name = item["FirstName"].strip()

        # fixes bad processing of Reps' names in NH CSV List Page
        first_name = first_name.replace("Rich\x82", "Riché")
        last_name = last_name.replace("No\x89l", "Noël")

        middle_name = item["MiddleName"].strip()
        name = f"{first_name} {middle_name} {last_name}"

        leg_body = item["LegislativeBody"]
        if leg_body == "H":
            chamber = "lower"
        elif leg_body == "S":
            chamber = "upper"

        district_county = item["County"]
        district_num = item["District"]
        district = f"{district_county} {district_num.lstrip('0')}"

        party_dict = {"d": "Democratic", "r": "Republican", "i": "Independent"}
        party = party_dict[item["party"].lower()]

        p = ScrapePerson(
            name=name, state="nh", chamber=chamber, district=district, party=party
        )

        p.family_name = last_name
        p.given_name = first_name

        county = item["County"]
        if county:
            p.extras["county"] = county

        elected_status = item["electedStatus"].strip()
        if elected_status:
            p.extras["elected status"] = elected_status

        addr = item["Address"].strip()
        if addr:
            addr += " "
            if item["address2"].strip():
                addr += item["address2"]
                addr += " "
            addr += item["city"]
            addr += ", NH "
            addr += item["Zipcode"]
            # NH site only gives district/home address for Representatives
            #  and only gives capitol address for Senators
            #  (this is true even on member detail pages)
            if chamber == "lower":
                p.district_office.address = addr
                p.district_office.voice = item["Phone"]
            else:
                p.capitol_office.address = addr
                p.capitol_office.voice = item["Phone"]

        if item["WorkEmail"].strip():
            p.email = item["WorkEmail"].strip()

        if item["GenderCode"].strip():
            p.extras["gender code"] = item["GenderCode"].strip()

        if chamber == "upper":
            detail_link = (
                "http://www.gencourt.state.nh.us/Senate/"
                f"members/webpages/district{district_num}.aspx"
            )
            p.add_source(detail_link)
            p.add_link(detail_link, note="member detail page")
            return SenateDetail(p, source=detail_link)
        else:
            house_name_key = f"{last_name}, {first_name}"
            house_val = self.house_url_vals[house_name_key]
            detail_link = (
                "http://www.gencourt.state.nh.us/house/"
                f"members/member.aspx?pid={house_val}"
            )
            p.add_source(detail_link)
            p.add_link(detail_link, note="member detail page")
            return HouseDetail(p, source=detail_link)
