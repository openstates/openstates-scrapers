from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("img").match(self.root)[6].get("src")
        p.image = img

        addresses = CSS("address").match(self.root)
        cap_addr = ""
        cap_phone = None
        cap_fax = None
        if p.chamber == "upper":
            lines = XPath("text()").match(addresses[0])
        else:
            lines = XPath("text()").match(addresses[-1])
        for line in lines:
            if re.search(r"(Senator|Hon\.)", line.strip()):
                continue
            elif re.search(r"FAX", line.strip()):
                cap_fax = line.strip()
            elif re.search(r"\(\d{3}\)\s\d{3}-\d{4}", line.strip()):
                cap_phone = line.strip()
            else:
                addr_lines = line.strip().split("\n")
                for cap_line in addr_lines:
                    cap_addr += cap_line.strip()
                    cap_addr += " "
        p.capitol_office.address = cap_addr.strip()
        if cap_phone:
            p.capitol_office.voice = cap_phone
        if cap_fax:
            cap_fax = re.search(r"FAX:\s(.+)", cap_fax).groups()[0]
            p.capitol_office.fax = cap_fax

        return p


class LegList(HtmlListPage):
    selector = CSS("div.MemberInfoList-MemberWrapper")

    def process_item(self, item):
        name_dirty = CSS("a").match_one(item).text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        district = CSS("br").match_one(item).tail.strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        party = CSS("b").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"
        elif party == "(I)":
            party = "Independent"

        p = ScrapePerson(
            name=name,
            state="pa",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=S&sort=alpha"
    )
    chamber = "upper"


class House(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=H&sort=alpha"
    )
    chamber = "lower"
