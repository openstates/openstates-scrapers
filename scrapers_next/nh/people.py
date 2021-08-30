import io
import csv
from spatula import URL, CsvListPage  # HtmlPage, CSS, XPath, HtmlListPage
from openstates.models import ScrapePerson
from dataclasses import dataclass

# import re


@dataclass
class PartialPerson:
    name: str
    chamber: str
    district: str
    source: str
    # staff_name: str
    # staff_email: str


# 24 total senators
# 395 total representatives?


# class SenDetail(HtmlPage):
#     input_type = PartialPerson

#     def process_page(self):
#         party = CSS("span.MemberHeader").match_one(self.root).text_content().strip()
#         party = re.search(r"(.+)\(([A-Z])-.+\)", party).groups()[1]

#         if party == "D":
#             party = "Democratic"
#         elif party == "R":
#             party = "Republican"

#         p = ScrapePerson(
#             name=self.input.name,
#             state="nh",
#             chamber=self.input.chamber,
#             district=self.input.district,
#             party=party,
#         )

#         p.add_source(self.input.source)
#         p.add_source(self.source.url)
#         p.add_link(self.source.url, note="homepage")

#         p.extras["staff name"] = self.input.staff_name
#         p.extras["staff email"] = self.input.staff_email

#         img = CSS("img.auto-style2").match_one(self.root).get("src")
#         p.image = img

#         contact_info = XPath("//*[@id='page_content']/table/tr[2]/td//strong[3]").match(
#             self.root
#         )[0]
#         cap_addr = contact_info.getnext().tail.strip()
#         cap_addr += " "
#         cap_addr += contact_info.getnext().getnext().tail.strip()
#         cap_addr += " "
#         cap_addr += contact_info.getnext().getnext().getnext().tail.strip()
#         p.capitol_office.address = cap_addr

#         if (
#             self.source.url
#             == "http://gencourt.state.nh.us/Senate/members/webpages/district14.aspx"
#         ):
#             phone = CSS("table tr td strong").match(self.root)[5].tail.strip()
#         else:
#             phone = (
#                 XPath(
#                     "//*[@id='page_content']/table/tr[2]/td//strong[contains(text(), 'Phone:')]"
#                 )
#                 .match(self.root)[0]
#                 .tail.strip()
#             )
#             phone = re.search(r"(\d{3}-\d{3}-\d{4})(.+)?", phone).groups()[0]
#             p.capitol_office.voice = phone

#         email = CSS("table tr td a").match(self.root)[1].text_content().strip()
#         p.email = email

#         return p


# class Senate(HtmlListPage):
#     source = URL("http://gencourt.state.nh.us/Senate/members/senate_roster.aspx")
#     selector = CSS("div#roseterWrap > div", num_items=24)

#     def process_item(self, item):

#         header_line = CSS("div").match(item)[0].text_content().strip()
#         header_line_lst = re.search(
#             r"District\s(.+)\s-\sSenator\s(.+)", header_line
#         ).groups()

#         district = header_line_lst[0]
#         if district[0] == "0":
#             district = district[1]
#         name = header_line_lst[1].strip()

#         staff = CSS("a").match(item)[1]
#         staff_email = staff.get("href")
#         staff_email = re.search(r"mailto:(.+)", staff_email).groups()[0]
#         staff_name = staff.text_content().strip()

#         partial = PartialPerson(
#             name=name,
#             chamber="upper",
#             district=district,
#             source=self.source.url,
#             staff_name=staff_name,
#             staff_email=staff_email,
#         )

#         detail_link = CSS("a").match(item)[0].get("href")

#         return SenDetail(partial, source=detail_link)


# class House(HtmlPage):
#     source = URL("http://gencourt.state.nh.us/house/members/default.aspx")

#     def process_page(self):
#         members = XPath("//*[@id='ContentPlaceHolder1_ddlReps']/option").match(
#             self.root
#         )
#         print(len(members))
#         # for member in members:
#         # print(member.text_content())


class Legislators(CsvListPage):
    def postprocess_response(self) -> None:
        self.reader = csv.DictReader(io.StringIO(self.response.text), delimiter="\t")

    source = URL("http://gencourt.state.nh.us/downloads/members.txt")

    def process_item(self, item):
        lastname = item["LastName"]
        firstname = item["FirstName"]
        middlename = item["MiddleName"]
        name = firstname + " " + middlename + " " + lastname

        legislativebody = item["LegislativeBody"]
        if legislativebody == "H":
            chamber = "lower"
        elif legislativebody == "S":
            chamber = "upper"

        district = item["District"]

        # 39 out of 116 legislators have incomplete info (len(member) < 19)
        # 24 senators and 15 reps
        # if chamber == "upper":
        #     if len(district) == 1:
        #         district_id = "0" + district
        #     else:
        #         district_id = district
        #     # detail_link = f"http://www.gencourt.state.nh.us/Senate/members/webpages/district{district_id}.aspx"

        party = item["party"]
        if party == "D" or party == "d":
            party = "Democratic"
        elif party == "R" or party == "r":
            party = "Republican"

        p = ScrapePerson(
            name=name, state="nh", chamber=chamber, district=district, party=party
        )

        p.add_source(self.source.url)

        p.family_name = lastname
        p.given_name = firstname

        county = item["County"]
        if county != "":
            p.extras["county"] = county

        electedStatus = item["electedStatus"].strip()
        if electedStatus != "":
            p.extras["elected status"] = electedStatus

        addr = item["Address"].strip()
        if addr != "":
            addr += " "
            if item["address2"].strip() != "":
                addr += item["address2"]
                addr += " "
            addr += item["city"]
            addr += ", NH "
            addr += item["Zipcode"]
            if item["Phone"].strip() != "":
                p.add_office(
                    contact_type="Primary Office", address=addr, voice=item["Phone"]
                )
            else:
                p.add_office(contact_type="Primary Office", address=addr)
            # is this primary office? or district office?

        if item["WorkEmail"].strip() != "":
            p.email = item["WorkEmail"].strip()

        if item["GenderCode"].strip() != "":
            p.extras["gender code"] = item["GenderCode"].strip()

        return p
