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
            capitol_fax,
            district_addr,
            district_phone,
            district_fax,
            email,
        ) = self.process_addrs_try_two()
        # if not capitol_addr:
        #     return None

        p.capitol_office.address = capitol_addr
        p.capitol_office.voice = capitol_phone
        if capitol_fax:
            p.capitol_office.fax = capitol_fax
        if district_addr:
            p.district_office.address = district_addr
        if district_phone:
            p.district_office.voice = district_phone
        if district_fax:
            p.district_office.fax = district_fax
        if email:
            p.email = email

        return p

    def process_addrs_try_two(self):
        (
            capitol_addr,
            cap_phone,
            capitol_fax,
            district_addr,
            dis_phone,
            dis_fax,
            email,
        ) = (None, None, None, None, None, None, None)
        addresses = CSS("body table tr td.member").match(self.root)
        line_number = 0
        district_addr_lines = 0
        for line in addresses:
            line = line.text_content()
            if (
                line == "Springfield Office:"
                or line == "District Office:"
                or line == "Additional District Addresses"
                or line.startswith("Senator")
                or line.startswith("Representative")
                or line.startswith("Years served:")
                or line == ""
            ):
                line_number += 1
                continue

            if not capitol_addr:
                capitol_addr = line
                line_number += 1
            elif line_number in [2, 3] and not line.startswith("("):
                capitol_addr += " "
                capitol_addr += line
                line_number += 1
            elif not cap_phone and line.startswith("("):
                cap_phone = line
                line_number += 1
            elif (line_number in [4, 5]) and re.search(r"FAX", line):
                capitol_fax = re.search(r"(.+)\sFAX", line).groups()[0]
                line_number += 1
            elif not district_addr:
                district_addr = line
                line_number += 1
                district_addr_lines += 1
            elif district_addr_lines == 1:
                district_addr += " "
                district_addr += line
                line_number += 1
                district_addr_lines += 1
            elif (
                district_addr_lines == 2
                and not line.strip().startswith("(")
                and not re.search(r"Email:", line)
            ):
                district_addr += " "
                district_addr += line
                line_number += 1
                district_addr_lines += 1
            elif not dis_phone:
                dis_phone = line
                line_number += 1
            elif re.search(r"FAX", line):
                dis_fax = re.search(r"(.+)\sFAX", line).groups()[0]
                line_number += 1
            elif re.search(r"Email:\s", line.strip()):
                email = re.search(r"Email:\s(.+)", line).groups()[0].strip()
                line_number += 1

        # print(capitol_addr)
        # print(cap_phone)
        # print(capitol_fax)
        # print(district_addr)
        # print(dis_phone)
        # print(dis_fax)
        # print(email)
        return (
            capitol_addr,
            cap_phone,
            capitol_fax,
            district_addr,
            dis_phone,
            dis_fax,
            email,
        )

    def fax_or_email(self, email_or_fax):
        if email_or_fax == "" or email_or_fax == "Additional District Addresses":
            return (None, None)
        elif re.search(r"FAX", email_or_fax):
            return (re.search(r"(.+)\sFAX", email_or_fax).groups()[0], "fax")
        else:
            return (
                re.search(r"Email:\s(.+)", email_or_fax).groups()[0].strip(),
                "email",
            )

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
            return (capitol_addr, cap_phone, None, None, None, None, None)
        elif len(addresses) == 10:
            # 3 house links have a length of 10
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=3006
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2994
            # https://ilga.gov/house/Rep.asp?GA=102&MemberID=2949
            # 0 senate links have a length of 10
            # no fax or email info
            cap_addr_line1 = addresses[1].text_content()
            cap_addr_line2 = addresses[2].text_content()
            cap_phone = addresses[3].text_content()
            dis_addr_line1 = addresses[6].text_content()
            dis_addr_line2 = addresses[7].text_content()
            dis_phone = addresses[8].text_content()
            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            district_addr = dis_addr_line1 + " " + dis_addr_line2
            return (capitol_addr, cap_phone, None, district_addr, dis_phone, None, None)
        elif len(addresses) == 11:
            # no capitol fax listed
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
                district_fax = None
            elif (
                self.source.url == "https://ilga.gov/house/Rep.asp?GA=102&MemberID=3003"
            ):
                # another special case, additional office link
                email = None
                district_fax = None
                dis_phone = addresses[8].text_content()
                district_addr = dis_addr_line1 + " " + dis_addr_line2
            else:
                dis_phone = addresses[8].text_content()
                email_or_fax = addresses[9].text_content()
                district_addr = dis_addr_line1 + " " + dis_addr_line2

                (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                if e_or_f_sting == "fax":
                    district_fax = email_or_fax
                    email = None
                else:
                    email = email_or_fax.strip()
                    district_fax = None

            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            return (
                capitol_addr,
                cap_phone,
                None,
                district_addr,
                dis_phone,
                district_fax,
                email,
            )
        elif len(addresses) == 12:
            # 42 house links have a length of 12
            # 10 senate links ahve a length of 12
            if re.search(r"(Senator|Representative)", addresses[1].text_content()):
                cap_addr_line1 = addresses[2].text_content()
                cap_addr_line2 = addresses[3].text_content()
                cap_phone = addresses[4].text_content()
                capitol_fax = None
                dis_addr_line1 = addresses[8].text_content()
                dis_addr_line2 = addresses[9].text_content()
                dis_phone = addresses[10].text_content()
                capitol_addr = cap_addr_line1 + " " + cap_addr_line2
                district_addr = dis_addr_line1 + " " + dis_addr_line2
                email = None
                district_fax = None
            else:
                cap_addr_line1 = addresses[1].text_content()
                cap_addr_line2 = addresses[2].text_content()
                cap_phone = addresses[3].text_content()

                email_or_fax = addresses[4].text_content()
                (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                if e_or_f_sting == "fax":
                    capitol_fax = email_or_fax
                    dis_addr_line1 = addresses[7].text_content()
                    dis_addr_line2 = addresses[8].text_content()
                    district_addr = dis_addr_line1 + " " + dis_addr_line2
                    dis_phone = addresses[9].text_content()
                    email_or_fax = addresses[10].text_content()
                    (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                    if e_or_f_sting == "fax":
                        district_fax = email_or_fax
                        email = None
                    else:
                        email = email_or_fax.strip()
                        district_fax = None
                else:
                    capitol_fax = None
                    dis_addr_line1 = addresses[6].text_content()
                    if re.search(r"Mail\sOnly", addresses[7].text_content()):
                        dis_addr_line2 = ""
                    else:
                        dis_addr_line2 = addresses[7].text_content()

                    if addresses[8].text_content().startswith("("):
                        district_addr = dis_addr_line1 + " " + dis_addr_line2
                        dis_phone = addresses[8].text_content()
                        district_fax = addresses[9].text_content()
                        district_fax = re.search(r"(.+)\sFAX", district_fax).groups()[0]
                        email = addresses[10].text_content()
                        email = re.search(r"Email:\s(.+)", email).groups()[0].strip()
                    else:
                        dis_addr_line3 = addresses[8].text_content()
                        district_addr = (
                            dis_addr_line1 + " " + dis_addr_line2 + " " + dis_addr_line3
                        )
                        dis_phone = addresses[9].text_content()
                        email_or_fax = addresses[10].text_content()
                        (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                        if e_or_f_sting == "fax":
                            district_fax = email_or_fax
                            email = None
                        else:
                            email = email_or_fax.strip()
                            district_fax = None

                capitol_addr = cap_addr_line1 + " " + cap_addr_line2

            return (
                capitol_addr,
                cap_phone,
                capitol_fax,
                district_addr,
                dis_phone,
                district_fax,
                email,
            )
        elif len(addresses) == 13:
            # 28 house links have a length of 13
            # 32 senate links ahve a length of 13
            if re.search(r"(Senator|Representative)", addresses[1].text_content()):
                cap_addr_line1 = addresses[2].text_content()
                cap_addr_line2 = addresses[3].text_content()
                cap_phone = addresses[4].text_content()
                capitol_fax = None
                dis_addr_line1 = addresses[8].text_content()
                dis_addr_line2 = addresses[9].text_content()
                if addresses[10].text_content().startswith("("):
                    dis_addr_line3 = ""
                    dis_phone = addresses[10].text_content()
                    email_or_fax = addresses[11].text_content()
                    (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                    dis_fax = email_or_fax
                    email = None
                else:
                    dis_addr_line3 = addresses[10].text_content()
                    dis_phone = addresses[11].text_content()
                    dis_fax = None
                    email = None
            else:
                cap_addr_line1 = addresses[1].text_content()
                cap_addr_line2 = addresses[2].text_content()
                cap_phone = addresses[3].text_content()
                email_or_fax = addresses[4].text_content()
                (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)

                if e_or_f_sting == "fax":
                    capitol_fax = email_or_fax
                    dis_addr_line1 = addresses[7].text_content()
                    dis_addr_line2 = addresses[8].text_content()
                    if addresses[9].text_content().startswith("("):
                        dis_addr_line3 = ""
                        dis_phone = addresses[9].text_content()
                        dis_fax = re.search(
                            r"(.+)\sFAX", addresses[10].text_content()
                        ).groups()[0]
                        email = (
                            re.search(r"Email:\s(.+)", addresses[11].text_content())
                            .groups()[0]
                            .strip()
                        )
                    else:
                        dis_addr_line3 = addresses[9].text_content()
                        dis_phone = addresses[10].text_content()
                        email = (
                            re.search(r"Email:\s(.+)", addresses[11].text_content())
                            .groups()[0]
                            .strip()
                        )
                else:
                    capitol_fax = None
                    dis_addr_line1 = addresses[6].text_content()
                    dis_addr_line2 = addresses[7].text_content()
                    if addresses[8].text_content().startswith("("):
                        dis_addr_line3 = ""
                        dis_phone = addresses[8].text_content()
                        # dis_fax = addresses[9].text_content()
                        dis_fax = re.search(
                            r"(.+)\sFAX", addresses[9].text_content()
                        ).groups()[0]
                        email = (
                            re.search(r"Email:\s(.+)", addresses[10].text_content())
                            .groups()[0]
                            .strip()
                        )
                    else:
                        dis_addr_line3 = addresses[8].text_content()
                        dis_phone = addresses[9].text_content()
                        dis_fax = addresses[10].text_content()
                        email = (
                            re.search(r"Email:\s(.+)", addresses[11].text_content())
                            .groups()[0]
                            .strip()
                        )

                """
                email_or_fax = addresses[11].text_content()
                (email_or_fax, e_or_f_sting) = self.fax_or_email(email_or_fax)
                if e_or_f_sting == 'fax':
                    dis_fax = email_or_fax
                    email = None
                else:
                    email = email_or_fax.strip()
                    dis_fax = None
                """

            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            district_addr = dis_addr_line1 + " " + dis_addr_line2 + " " + dis_addr_line3
            district_addr = district_addr.strip()

            print(capitol_addr)
            print(cap_phone)
            if capitol_fax:
                print(capitol_fax)
            print(district_addr)
            print(dis_phone)
            if dis_fax:
                print(dis_fax)
            if email:
                print(email)

            return (
                capitol_addr,
                cap_phone,
                capitol_fax,
                district_addr,
                dis_phone,
                dis_fax,
                email,
            )
        elif len(addresses) == 14:
            # 10 house links have a length of 14
            # 16 senate links ahve a length of 14
            return (None, None, None, None, None, None, None)
            """
            cap_addr_line1 = addresses[2].text_content()
            cap_addr_line2 = addresses[3].text_content()
            cap_phone = addresses[4].text_content()
            dis_addr_line1 = addresses[8].text_content()
            dis_addr_line2 = addresses[9].text_content()
            if addresses[10].text_content().startswith("("):
                dis_phone = addresses[10].text_content()
                dis_fax = addresses[11].text_content()
            """
            # dis_fax = re.search(r"(.+)\sFAX", dis_fax).groups()[0]
            # district_addr = dis_addr_line1 + " " + dis_addr_line2
            """
            else:
                dis_addr_line3 = addresses[10].text_content()
                dis_phone = addresses[11].text_content()
                if addresses[12].text_content().startswith("("):
                    dis_fax = addresses[12].text_content()
            """
            # dis_fax = re.search(r"(.+)\sFAX", dis_fax).groups()[0]
            """
                else:
                    dis_fax = None
                district_addr = (
                    dis_addr_line1 + " " + dis_addr_line2 + " " + dis_addr_line3
                )
            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            return (
                capitol_addr,
                cap_phone,
                None,
                district_addr,
                dis_phone,
                dis_fax,
                None,
            )
            """
        elif len(addresses) == 15:
            # 0 house links have a length of 15
            # 1 senate link has a length of 15
            # https://ilga.gov/senate/Senator.asp?GA=102&MemberID=2899
            cap_addr_line1 = addresses[2].text_content()
            cap_addr_line2 = addresses[3].text_content()
            cap_phone = addresses[4].text_content()
            dis_addr_line1 = addresses[8].text_content()
            dis_addr_line2 = addresses[9].text_content()
            dis_addr_line3 = addresses[10].text_content()
            dis_phone = addresses[11].text_content()
            dis_fax = addresses[12].text_content()
            dis_fax = re.search(r"(.+)\sFAX", dis_fax).groups()[0]
            capitol_addr = cap_addr_line1 + " " + cap_addr_line2
            district_addr = dis_addr_line1 + " " + dis_addr_line2 + " " + dis_addr_line3
            return (
                capitol_addr,
                cap_phone,
                None,
                district_addr,
                dis_phone,
                dis_fax,
                None,
            )


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
