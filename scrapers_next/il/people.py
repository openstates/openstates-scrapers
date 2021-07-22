from spatula import CSS, HtmlListPage, HtmlPage
from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("body table tr td img").match(self.root)[2].get("src")
        p.image = img

        captiol_addr = CSS("body table tr td").match(self.root)[31].text_content()
        captiol_addr += " "
        captiol_addr += CSS("body table tr td").match(self.root)[32].text_content()
        captiol_phone = CSS("body table tr td").match(self.root)[33].text_content()

        p.capitol_office.address = captiol_addr
        p.capitol_office.voice = captiol_phone

        district_addr = CSS("body table tr td").match(self.root)[37].text_content()
        district_addr += " "
        district_addr += CSS("body table tr td").match(self.root)[38].text_content()
        district_addr += " "
        district_addr += CSS("body table tr td").match(self.root)[39].text_content()
        district_phone = CSS("body table tr td").match(self.root)[40].text_content()

        p.district_office.address = district_addr
        p.district_office.voice = district_phone

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
