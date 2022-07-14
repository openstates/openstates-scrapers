from spatula import CSS, HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    fax_re = re.compile(r"(.+)\sFAX")
    email_re = re.compile(r"Email:\s(.+)")

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
        """
        This terrible for loop brought to you by the IL legislature page's terrible
        formatting! e.g.
        <table width="100%" border="0"><tr><td class="member" width="100%" valign="top"><br><b>Springfield Office:</b></td></tr><tr><td class="member" width="100%">Senator 27th District</td></tr><tr><td class="member" width="100%">Stratton Office Building</td></tr><tr><td class="member" width="100%">Section C , Room F</td></tr><tr><td class="member" width="100%">Springfield, IL &nbsp;&nbsp;62706    </td></tr><tr><td class="member" width="100%">(217) 782-4471</td></tr><tr><td class="member" width="100%">&nbsp;</td></tr></table><table border="0" width="100%"><tr><td class="member" width="100%"></td></tr><tr><td class="member" width="100%"><b>District Office:</b></td></tr><tr><td class="member" width="100%">171 W. Wing St.</td></tr><tr><td class="member" width="100%">Suite 202</td></tr><tr><td class="member" width="100%">Arlington Heights, IL&nbsp;&nbsp;60005    </td></tr><tr><td class="member" width="100%">(847) 749-1880</td></tr></table></td></tr></table><br><table border="0" width="390"><tr><td class="member"><b>Years served: </b> <br><br><b>Committee assignments:</b> Ethics (Chair); Commerce; Health; Insurance; Local Government; App-Constitutional Offices (Sub-Vice-Chair); App-Health; Subcommittee on Medicaid (Sub-Chair); Sub. on Managed Care Organizations; Subcommittee on Special Issues (H); Redistricting- Northwest Cook (Sub-Chair).<br><br><b>Biography:</b> Lifelong resident of the Northwest suburbs. Full-time state legislator. Retired from health care industry. Bachelor's degree in history from the University of Illinois Urbana-Champaign; law degree from DePaul University College of Law. Mother of two adult children, Kevin and Gillian. Resident of Arlington Heights since 1991.
         """
        for line_number, line in enumerate(addresses):
            line = line.text_content().strip()
            if (
                not line
                or line
                in [
                    "Springfield Office:",
                    "District Office:",
                    "Additional District Addresses",
                ]
                or any(
                    line.startswith(s)
                    for s in ["Senator", "Representative", "Years served:"]
                )
            ):
                continue

            if not capitol_addr:
                capitol_addr = line
            elif line_number in [2, 3] and not line.startswith("("):
                capitol_addr += f" {line}"
            elif not cap_phone and line.startswith("("):
                cap_phone = line
            elif line_number in [4, 5] and "FAX" in line:
                capitol_fax = self.fax_re.search(line).groups()[0]
            elif not district_addr:
                district_addr = line
                district_addr_lines += 1
            elif district_addr_lines == 1:
                district_addr += f" {line}"
                district_addr_lines += 1
            elif (
                district_addr_lines == 2
                and not line.strip().startswith("(")
                and "Email:" not in line
            ):
                district_addr += " "
                district_addr += line
                district_addr_lines += 1
            elif not dis_phone and line.startswith("("):
                dis_phone = line
            elif "FAX" in line:
                dis_fax = self.fax_re.search(line).groups()[0]
            elif "Email: " in line.strip():
                email = self.email_re.search(line).groups()[0].strip()

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
