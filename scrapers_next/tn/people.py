from spatula import CSS, URL, HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        addr_lst = XPath(
            "/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[1]/text()"
        ).match(self.root)
        cap_address = ""
        for line in addr_lst:
            if re.search(r"Phone", line):
                cap_phone = re.search(r"Phone:?\s(.+)", line).groups()[0].strip()
                p.capitol_office.voice = cap_phone
            elif re.search(r"Fax", line):
                cap_fax = re.search(r"Fax:?\s(.+)", line).groups()[0].strip()
                p.capitol_office.fax = cap_fax
            elif re.search(r"\d?-?\d{3}-\d{3}-\d{4}", line):
                p.extras["extra phone"] = line.strip()
            else:
                cap_address += line.strip()
                cap_address += " "
        p.capitol_office.address = cap_address.strip()

        img = CSS("img.framed-photo").match_one(self.root).get("src")
        p.image = img

        return p


class Legislators(HtmlListPage):
    selector = CSS("tbody tr")

    def process_item(self, item):
        name_dirty = CSS("td").match(item)[1].text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("td").match(item)[2].text_content().strip()
        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"

        district = CSS("td").match(item)[4].text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="tn",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("td a").match(item)[1].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        email = CSS("td a").match(item)[0].get("href")
        email = re.search(r"mailto:(.+)", email).groups()[0]
        p.email = email

        # this is also being grabbed above in capitol_office.address
        office_room = CSS("td").match(item)[5].text_content().strip()
        p.extras["office"] = office_room

        return LegDetail(p, source=detail_link)


class Senate(Legislators):
    source = URL("https://www.capitol.tn.gov/senate/members/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.capitol.tn.gov/house/members/")
    chamber = "lower"
