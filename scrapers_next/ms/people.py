from spatula import URL, HtmlPage, CSS, SelectorError
from openstates.models import ScrapePerson
from itertools import zip_longest
from dataclasses import dataclass
import re

CAP_ADDRESS = """P. O. Box 1018;Jackson, MS 39215"""


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
        district = CSS("district").match_one(self.root).text_content().strip()
        party = CSS("party").match_one(self.root).text_content().strip()

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

        try:
            email = CSS("email").match_one(self.root).text_content().strip()
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
        except SelectorError:
            pass

        img_id = CSS("img_name").match_one(self.root).text_content().strip()
        if self.input.chamber == "upper":
            img = "http://billstatus.ls.state.ms.us/members/senate/" + img_id
        else:
            img = "http://billstatus.ls.state.ms.us/members/house/" + img_id
        p.image = img

        if self.input.title != "member":
            p.extras["title"] = self.input.title

        last_name = CSS("u_mem_nam").match_one(self.root).text_content().strip()
        if re.search(r"\(\d{1,2}[a-z]{2}\)", last_name):
            last_name = re.search(r"(.+)\s\(\d{1,2}[a-z]{2}\)", last_name).groups()[0]
        p.family_name = last_name

        try:
            occupation = CSS("occupation").match_one(self.root).text_content().strip()
            if occupation != "":
                p.extras["occupation"] = occupation
        except SelectorError:
            pass

        try:
            education_lst = CSS("education").match(self.root)
            if len(education_lst) > 0:
                p.extras["education"] = []
                for ed in education_lst:
                    if ed.text_content().strip() != "":
                        p.extras["education"] += [ed.text_content().strip()]
        except SelectorError:
            pass

        county_lst = CSS("cnty_info").match(self.root)
        if len(county_lst) > 0:
            p.extras["counties represented"] = []
            for county in county_lst:
                if county.text_content().strip() != "":
                    p.extras["counties represented"] += [county.text_content().strip()]

        home_addr = ""
        h_address = CSS("h_address").match_one(self.root).text_content().strip()
        h_address2 = CSS("h_address2").match_one(self.root).text_content().strip()
        h_city = CSS("h_city").match_one(self.root).text_content().strip()
        h_zip = CSS("h_zip").match_one(self.root).text_content().strip()

        # Note that these are listed as 'Home Office' but adding to 'District Office'
        if h_address != "" and h_address2 != "":
            home_addr = (
                h_address + " " + h_address2 + " " + h_city + ", Mississippi " + h_zip
            )
            p.district_office.address = home_addr
        elif h_address != "":
            home_addr = h_address + " " + h_city + ", Mississippi " + h_zip
            p.district_office.address = home_addr

        h_phone = CSS("h_phone").match_one(self.root).text_content().strip()
        if h_phone != "":
            p.district_office.voice = h_phone

        cap_room = CSS("cap_room").match_one(self.root).text_content().strip()
        if cap_room != "":
            cap_addr = "Room %s %s" % (cap_room, CAP_ADDRESS)
        else:
            cap_addr = CAP_ADDRESS
        p.capitol_office.address = cap_addr

        cap_phone = CSS("cap_phone").match_one(self.root).text_content().strip()
        if cap_phone != "":
            p.capitol_office.voice = cap_phone

        b_phone = CSS("b_phone").match_one(self.root).text_content().strip()
        oth_phone = CSS("oth_phone").match_one(self.root).text_content().strip()
        oth_type = CSS("oth_type").match_one(self.root).text_content().strip()

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
        member_links = set()
        for member in members:
            children = member.getchildren()
            if not children:
                continue
            elif len(children) == 3:
                lt_gov = "President of the Senate"
                title = children[0].text_content().strip()
                if title == lt_gov:
                    continue

                name = children[1].text_content().strip()

                link_id = children[2].text_content().strip().lower()
                link = "http://billstatus.ls.state.ms.us/members/" + link_id
                member_links.add(link)

                partial_p = PartialPerson(
                    name=name,
                    title=title,
                    chamber=self.chamber,
                    source=self.source.url,
                )

                yield LegDetail(partial_p, source=link)
            else:
                for mem in grouper(member, 3):
                    name = mem[0].text_content().strip()

                    link_id = mem[1].text_content().strip().lower()
                    if not re.search(r"\.xml", link_id):
                        continue

                    link = "http://billstatus.ls.state.ms.us/members/" + link_id
                    if link in member_links:
                        continue
                    member_links.add(link)

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
