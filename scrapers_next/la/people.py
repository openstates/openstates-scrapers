from spatula import HtmlListPage, CSS, URL, HtmlPage
from openstates.models import ScrapePerson
import re


class LegislatorDetail(HtmlPage):
    def process_page(self):
        p = self.input

        district_addr = (
            CSS("span#body_FormView3_OFFICEADDRESS2Label")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        print(district_addr)
        # lxml.etree.tostring(font).replace(b”<br>“, b”\n”).splitlines()
        # phone = CSS("span#body_FormView3_DISTRICTOFFICEPHONELabel").match_one(self.root).text_content().strip()
        # fax = CSS("span#body_FormView3_FAXNUMBERLabel").match_one(self.root).text_content().strip()

        return p


class Legislators(HtmlListPage):
    selector = CSS("fieldset div.media")

    def process_item(self, item):
        name_dirty = CSS("h4 span").match_one(item).text_content().strip()
        if re.search(r"Vacant", name_dirty):
            self.skip()
        name_dirty = name_dirty.split(", ")
        last_name = name_dirty[0]
        first_name = name_dirty[1]
        name = first_name + " " + last_name

        district = CSS("i.fa.fa-map").match_one(item).getnext().text_content().strip()
        party = CSS("i.fa.fa-users").match_one(item).getnext().text_content().strip()
        if party == "Democrat":
            party = "Democratic"
        email = CSS("a").match(item)[2].text_content().strip()
        img = CSS("img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="la",
            party=party,
            district=district,
            chamber=self.chamber,
            email=email,
            image=img,
        )

        # district_addr = CSS("i.fa.fa-map-marker").match_one(item).getnext().text_content().strip().split("\n")
        # p.district_office.address = district_addr
        # print(len(district_addr))

        detail_link = CSS("a").match(item)[1].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegislatorDetail(p, source=detail_link)


class Senate(Legislators):
    source = URL("https://senate.la.gov/Senators_FullInfo")
    chamber = "upper"


class House(Legislators):
    source = URL("https://house.louisiana.gov/H_Reps/H_Reps_FullInfo")
    chamber = "lower"
