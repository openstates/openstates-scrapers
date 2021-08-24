from spatula import URL, HtmlPage
from openstates.models import ScrapePerson
from itertools import zip_longest
from dataclasses import dataclass
import re

CAP_ADDRESS = """P. O. Box 1018
Jackson, MS 39215"""


@dataclass
class PartialPerson:
    name: str
    title: str
    chamber: str
    source: str


# source https://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class LegDetail(HtmlPage):
    input_type = PartialPerson

    def process_page(self):
        if self.source.url == "http://ltgovhosemann.ms.gov/":
            return None

        district = self.root.cssselect("district")[0].text_content()
        party = self.root.cssselect("party")[0].text_content()

        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"
        elif party == "I":
            party = "Independent"

        # no party listed on page
        if self.input.name in ["Lataisha Jackson", "John G. Faulkner"]:
            party = "Democratic"

        p = ScrapePerson(
            name=self.input.name,
            state="ms",
            chamber=self.input.chamber,
            district=district,
            party=party,
        )

        p.add_source(self.input.source)
        p.add_source(self.source.url)
        p.add_link(self.source.url, note="homepage")

        email = self.root.cssselect("email")
        if len(email) > 0:
            email = email[0].text_content().strip()
            if (
                not re.search(r"@senate.ms.gov", email)
                and self.input.chamber == "upper"
            ):
                email = email + "@senate.ms.gov"
            elif (
                not re.search(r"@house.ms.gov", email) and self.input.chamber == "lower"
            ):
                email = email + "@house.ms.gov"
            p.email = email

        img_id = self.root.cssselect("img_name")[0].text_content()
        if self.input.chamber == "upper":
            img = "http://billstatus.ls.state.ms.us/members/senate/" + img_id
        else:
            img = "http://billstatus.ls.state.ms.us/members/house/" + img_id
        p.image = img

        if self.input.title != "member":
            p.extras["title"] = self.input.title

        last_name = self.root.cssselect("u_mem_nam")[0].text_content()
        if re.search(r"\(\d{1,2}[a-z]{2}\)", last_name):
            last_name = re.search(r"(.+)\s\(\d{1,2}[a-z]{2}\)", last_name).groups()[0]
        p.family_name = last_name

        occupation = self.root.cssselect("occupation")
        if len(occupation) > 0 and occupation[0].text_content().strip() != "":
            p.extras["occupation"] = occupation[0].text_content().strip()

        education_lst = self.root.cssselect("education")
        if len(education_lst) > 0:
            p.extras["education"] = []
        for ed in education_lst:
            if ed.text_content().strip() != "":
                p.extras["education"] += [ed.text_content().strip()]

        county_lst = self.root.cssselect("cnty_info")
        if len(county_lst) > 0:
            p.extras["counties represented"] = []
        for county in county_lst:
            if county.text_content().strip() != "":
                p.extras["counties represented"] += [county.text_content().strip()]

        home_addr = ""
        h_address = self.root.cssselect("h_address")[0].text_content()
        h_address2 = self.root.cssselect("h_address2")[0].text_content()
        h_city = self.root.cssselect("h_city")[0].text_content()
        h_zip = self.root.cssselect("h_zip")[0].text_content()
        h_phone = self.root.cssselect("h_phone")[0].text_content()
        if h_address != "" and h_address2 != "":
            home_addr = (
                h_address + " " + h_address2 + " " + h_city + ", Mississippi " + h_zip
            )
        elif h_address != "":
            home_addr = h_address + " " + h_city + ", Mississippi " + h_zip

        if home_addr != "" and h_phone != "":
            p.add_office(contact_type="Home Office", address=home_addr, voice=h_phone)
        elif home_addr != "":
            p.add_office(contact_type="Home Office", address=home_addr)

        cap_room = self.root.cssselect("cap_room")[0].text_content().strip()
        if cap_room != "":
            cap_addr = "Room %s\n%s" % (cap_room, CAP_ADDRESS)
        else:
            cap_addr = CAP_ADDRESS
        p.capitol_office.address = cap_addr

        cap_phone = self.root.cssselect("cap_phone")[0].text_content()
        if cap_phone != "":
            p.capitol_office.voice = cap_phone

        b_phone = self.root.cssselect("b_phone")[0].text_content()
        oth_phone = self.root.cssselect("oth_phone")[0].text_content()
        oth_type = self.root.cssselect("oth_type")[0].text_content()
        if oth_phone != "" and oth_type == "F" and b_phone != "":
            p.extras["fax"] = oth_phone
            p.extras["other phone"] = b_phone
        elif oth_phone != "" and b_phone != "":
            p.extras["other phone1"] = oth_phone
            p.extras["other phone2"] = b_phone
        elif oth_phone != "":
            p.extras["other phone"] = oth_phone
        elif b_phone != "":
            p.extras["other phone"] = b_phone

        return p


class Legislators(HtmlPage):
    def process_page(self):
        members = self.root.getchildren()
        for member in members:
            children = member.getchildren()
            if children == []:
                continue
            elif len(children) == 3:
                title = children[0].text_content().strip()
                name = children[1].text_content().strip()
                link_id = children[2].text_content().strip()
                if link_id == "http://ltgovhosemann.ms.gov/":
                    link = link_id
                else:
                    link = "http://billstatus.ls.state.ms.us/members/" + link_id

                partial_p = PartialPerson(
                    name=name, title=title, chamber=self.chamber, source=self.source.url
                )

                yield LegDetail(partial_p, source=link)
            else:
                for mem in grouper(member, 3):
                    name = mem[0].text_content().strip()
                    # Dean Kirby listed twice (already scraped above)
                    if name == "Dean Kirby":
                        continue

                    link_id = mem[1].text_content().strip()
                    link = "http://billstatus.ls.state.ms.us/members/" + link_id

                    partial_p = PartialPerson(
                        name=name,
                        title="member",
                        chamber=self.chamber,
                        source=self.source.url,
                    )

                    yield LegDetail(partial_p, source=link)


class Senate(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/ss_membs.xml")
    chamber = "upper"


class House(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/hr_membs.xml")
    chamber = "lower"
