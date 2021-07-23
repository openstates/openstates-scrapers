from spatula import CSS, HtmlListPage, HtmlPage
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("body table tr td img").match(self.root)[2].get("src")
        p.image = img

        (
            capitol_addr,
            capitol_phone,
            district_addr,
            district_phone,
            email,
            district_fax,
        ) = self.process_addrs()
        if not capitol_addr:
            return None

        p.capitol_office.address = capitol_addr
        p.capitol_office.voice = capitol_phone
        if district_addr:
            p.district_office.address = district_addr
        if district_phone:
            p.district_office.voice = district_phone
        if email:
            p.email = email
        if district_fax:
            p.district_office.fax = district_fax

        return p

    def process_addrs(self):
        addresses = CSS("body table tr td.member").match(self.root)
        if len(addresses) == 7:
            # no district information
            # 1 house link has a length of 7
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=3012
            # 0 senate links have a length of 7
            cap_addr_line1 = addresses[1].text_content()
            cap_addr_line2 = addresses[2].text_content()
            cap_phone = addresses[3].text_content()
            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            return (capitol_addr, cap_phone, None, None, None, None)
        elif len(addresses) == 10:
            # 3 house links have a length of 10
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=3006
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2994
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2949
            # 0 senate links have a length of 10
            cap_addr_line1 = addresses[1].text_content()
            cap_addr_line2 = addresses[2].text_content()
            cap_phone = addresses[3].text_content()
            dis_addr_line1 = addresses[6].text_content()
            dis_addr_line2 = addresses[7].text_content()
            dis_phone = addresses[8].text_content()
            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            district_addr = dis_addr_line1 + " " + dis_addr_line2
            return (capitol_addr, cap_phone, district_addr, dis_phone, None, None)
        elif len(addresses) == 11:
            # 34 house links have a length of 11
            # 0 senate links have a length of 11
            cap_addr_line1 = addresses[1].text_content()
            cap_addr_line2 = addresses[2].text_content()
            cap_phone = addresses[3].text_content()
            dis_addr_line1 = addresses[6].text_content()
            dis_addr_line2 = addresses[7].text_content()

            # special case (extra line in district address)
            if self.source.url == "https://ilga.gov/house/Rep.asp?GA=102&MemberID=2945":
                dis_addr_line3 = addresses[8].text_content()
                dis_phone = addresses[9].text_content()
                district_addr = (
                    dis_addr_line1 + " " + dis_addr_line2 + " " + dis_addr_line3
                )
                email = None
                fax = None
            elif (
                self.source.url == "https://ilga.gov/house/Rep.asp?GA=102&MemberID=3003"
            ):
                # another special case, additional office link
                email = None
                fax = None
                dis_phone = addresses[8].text_content()
                district_addr = dis_addr_line1 + " " + dis_addr_line2
            else:
                dis_phone = addresses[8].text_content()
                email_or_fax = addresses[9].text_content()
                district_addr = dis_addr_line1 + " " + dis_addr_line2

                if re.search(r"FAX", email_or_fax):
                    fax = re.search(r"(.+)\sFAX", email_or_fax).groups()[0]
                    email = None
                    # p.district_office.fax = fax
                    # print(fax)
                else:
                    email = re.search(r"Email:\s(.+)", email_or_fax).groups()[0]
                    fax = None
                    # p.email = email.strip()
                    # print(email.strip())

            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            return (capitol_addr, cap_phone, district_addr, dis_phone, email, fax)
        elif len(addresses) == 12:
            return (None, None, None, None, None, None)
        elif len(addresses) == 13:
            return (None, None, None, None, None, None)
        elif len(addresses) == 14:
            return (None, None, None, None, None, None)
        elif len(addresses) == 15:
            return (None, None, None, None, None, None)

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
