import io
import csv
from spatula import URL, CsvListPage, HtmlPage, CSS, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class SenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("img.rounded").match_one(self.root).get("src")
        p.image = img

        contact_info = XPath("//strong[contains(text(), 'Contact Information')]").match(
            self.root
        )[0]
        cap_addr = contact_info.getnext().tail.strip()
        cap_addr += " "
        cap_addr += contact_info.getnext().getnext().tail.strip()
        cap_addr += " "
        cap_addr += contact_info.getnext().getnext().getnext().tail.strip()
        p.capitol_office.address = cap_addr

        try:
            phone = (
                XPath("//strong[contains(text(), 'Phone:')]")
                .match(self.root)[0]
                .tail.strip()
            )
            phone = re.search(r"(\d{3}-\d{3}-\d{4})(.+)?", phone).groups()[0]
            p.capitol_office.voice = phone
        except SelectorError:
            pass

        return p


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

        district_county = item["County"]
        district_num = item["District"]
        district = f"{district_county} {district_num.lstrip('0')}"

        party = item["party"]
        if party == "D" or party == "d":
            party = "Democratic"
        elif party == "R" or party == "r":
            party = "Republican"
        elif party in ["i", "I"]:
            party = "Independent"

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
                    classification="primary", address=addr, voice=item["Phone"]
                )
            else:
                p.add_office(classification="primary", address=addr)
            # is this primary office? or district office?

        if item["WorkEmail"].strip() != "":
            p.email = item["WorkEmail"].strip()

        if item["GenderCode"].strip() != "":
            p.extras["gender code"] = item["GenderCode"].strip()

        if chamber == "upper":
            detail_link = f"http://www.gencourt.state.nh.us/Senate/members/webpages/district{district_num}.aspx"
            p.add_source(detail_link)
            p.add_link(detail_link, note="homepage")
            return SenDetail(p, source=detail_link)

        # seat_number = seat_map[item["seatno"]]
        # detail_link = f"http://www.gencourt.state.nh.us/house/members/member.aspx?member={seat_number}"
        # return HouseDetail(p, source=detail_link)
        return p
