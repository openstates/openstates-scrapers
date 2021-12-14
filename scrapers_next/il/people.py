from spatula import CSS, HtmlListPage, HtmlPage, XPath
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
        ) = self.process_addrs()

        p.capitol_office.address = capitol_addr
        p.capitol_office.voice = capitol_phone or ""
        if capitol_fax:
            p.capitol_office.fax = capitol_fax
        if district_addr:
            p.district_office.address = district_addr
        if district_phone:
            p.district_office.voice = district_phone or ""
        if district_fax:
            p.district_office.fax = district_fax
        if email:
            p.email = email

        return p

    def process_addrs(self):
        """
        For a given detail page, len(CSS("body table tr td.member").match(self.root))
        can be either 7, 10, 11, 12, 13, 14, or 15. This function / for loop handles
        pages with varies number of 'address' lines.
        """
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
        district_addr_lines = 0
        for line_number, line in enumerate(addresses):
            line = line.text_content().strip()
            if (
                line == "Springfield Office:"
                or line == "District Office:"
                or line == ""
                or line == "Additional District Addresses"
                or line.startswith("Senator")
                or line.startswith("Representative")
                or line.startswith("Years served:")
            ):
                continue

            if not capitol_addr:
                capitol_addr = line
            elif line_number in [2, 3] and not line.startswith("("):
                capitol_addr += " "
                capitol_addr += line
            elif not cap_phone and line.startswith("("):
                cap_phone = line
            elif (line_number in [4, 5]) and re.search(r"FAX", line):
                capitol_fax = re.search(r"(.+)\sFAX", line).groups()[0]
            elif not district_addr:
                district_addr = line
                district_addr_lines += 1
            elif district_addr_lines == 1:
                district_addr += " "
                district_addr += line
                district_addr_lines += 1
            elif (
                district_addr_lines == 2
                and not line.strip().startswith("(")
                and not re.search(r"Email:", line)
            ):
                district_addr += " "
                district_addr += line
                district_addr_lines += 1
            elif not dis_phone:
                dis_phone = line
            elif re.search(r"FAX", line):
                dis_fax = re.search(r"(.+)\sFAX", line).groups()[0]
            elif re.search(r"Email:\s", line.strip()):
                email = re.search(r"Email:\s(.+)", line).groups()[0].strip()

        return (
            capitol_addr,
            cap_phone,
            capitol_fax,
            district_addr,
            dis_phone,
            dis_fax,
            email,
        )


class LegList(HtmlListPage):
    selector = XPath(".//form/table[1]/tr")

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
