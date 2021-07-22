from spatula import CSS, HtmlListPage, HtmlPage
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("body table tr td img").match(self.root)[2].get("src")
        p.image = img

        # print(len(CSS("body table tr td.member").match(self.root)))

        if len(CSS("body table tr td.member").match(self.root)) == 10:
            # 3 house links have a length of 10
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=3006
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2994
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2949
            # 0 senate links have a length of 10
            idx = 1
            # 1 addr, 2 addr, 3 phone, 6 addr, 7 addr, 8 phone
            return None
        elif len(CSS("body table tr td.member").match(self.root)) == 11:
            # 34 house links have a length of 11
            # 0 senate links have a length of 11
            idx = 1
            # 1 addr, 2 addr, 3 phone, 6 addr, 7 addr, 8 phone, 9 email
            email_or_fax = (
                CSS("body table tr td.member").match(self.root)[9].text_content()
            )
            if re.search(r"FAX", email_or_fax):
                fax = re.search(r"(.+)\sFAX", email_or_fax).groups()[0]
                p.district_office.fax = fax
                print(fax)
            else:
                email = re.search(r"Email:\s(.+)", email_or_fax).groups()[0]
                p.email = email.strip()
                print(email)
            # return None
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2945 special case
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=3003 additional office
        else:
            return None

        """
        elif len(CSS("body table tr td.member").match(self.root)) == 12:
            idx = 1
            # 1 addr, 2 addr, 3 phone, 6 addr, 7 addr, 8 addr, 9 phone, 10 email
        elif len(CSS("body table tr td.member").match(self.root)) == 13:
            idx = 1
            # 1 addr, 2 addr, 3 phone, 6 addr, 7 addr, 8 addr, 9 phone, 10 fax, 11 email
            # 2, 3, 4, 8, 9, 10, 11
        elif len(CSS("body table tr td.member").match(self.root)) == 14:
            idx = 2
            # 2 addr, 3 addr, 4 phone, 8 addr, 9 addr, 10 addr, 11 phone, 12 fax
        """

        # idx = 1

        captiol_addr = (
            CSS("body table tr td.member").match(self.root)[idx].text_content()
        )
        captiol_addr += " "
        captiol_addr += (
            CSS("body table tr td.member").match(self.root)[idx + 1].text_content()
        )
        captiol_phone = (
            CSS("body table tr td.member").match(self.root)[idx + 2].text_content()
        )

        p.capitol_office.address = captiol_addr
        p.capitol_office.voice = captiol_phone

        district_addr = (
            CSS("body table tr td.member").match(self.root)[idx + 5].text_content()
        )
        district_addr += " "
        district_addr += (
            CSS("body table tr td.member").match(self.root)[idx + 6].text_content()
        )
        # district_addr += " "
        # district_addr += CSS("body table tr td.member").match(self.root)[idx + 8].text_content()
        district_phone = (
            CSS("body table tr td.member").match(self.root)[idx + 7].text_content()
        )

        p.district_office.address = district_addr
        p.district_office.voice = district_phone

        # 12-14 for sen
        # 10-14 for house
        # print(captiol_addr)
        # print(captiol_phone)
        # print(district_addr)
        # print(district_phone)

        return p


class LegList(HtmlListPage):
    selector = CSS("form table tr")

    def process_item(self, item):
        # skip header rows
        if (
            len(CSS("td").match(item)) == 1
            or CSS("td").match(item)[0].get("class") == "header"
        ):
            self.skip()

        first_link = CSS("td a").match(item)[0]
        name = first_link.text_content()
        detail_link = first_link.get("href")

        # these are "Former Senate Members"
        former_members = [
            "Andy Manar",
            "Heather A. Steans",
            "Edward Kodatt",
            "Michael J. Madigan",
            "André Thapedi",
        ]
        if name in former_members:
            self.skip()

        district = CSS("td").match(item)[3].text_content()
        party_letter = CSS("td").match(item)[4].text_content()
        party_dict = {"D": "Democratic", "R": "Republican", "I": "Independent"}
        party = party_dict[party_letter]

        p = ScrapePerson(
            name=name,
            state="il",
            party=party,
            chamber=self.chamber,
            district=district,
        )

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegDetail(p, source=detail_link)


class House(LegList):
    source = "https://ilga.gov/house/default.asp?GA=102"
    chamber = "lower"


class Senate(LegList):
    source = "https://ilga.gov/senate/default.asp?GA=102"
    chamber = "upper"
