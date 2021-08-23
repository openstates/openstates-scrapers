from spatula import HtmlListPage, CSS, URL, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegislatorDetail(HtmlPage):
    def process_page(self):
        p = self.input

        district_addr_lst = XPath(
            "//*[@id='body_FormView3_OFFICEADDRESS2Label']/text()"
        ).match(self.root)
        district_addr_temp = ""
        district_addr1 = None
        district_addr2 = None
        district_addr3 = None

        for addr in district_addr_lst:
            district_addr_temp += addr.strip()
            if (
                re.search(r"L(A|a)\s\s?\s?\d{5}(-\d{4})?$", district_addr_temp)
                and not district_addr1
            ):
                district_addr1 = district_addr_temp
                district_addr_temp = ""
                p.district_office.address = district_addr1
            elif (
                re.search(r"L(A|a)\s\s?\s?\d{5}(-\d{4})?$", district_addr_temp)
                and not district_addr2
            ):
                district_addr2 = district_addr_temp
                district_addr_temp = ""
                p.extras["second address"] = district_addr2
            elif (
                re.search(r"L(A|a)\s\s?\s?\d{5}(-\d{4})?$", district_addr_temp)
                and not district_addr3
            ):
                district_addr3 = district_addr_temp
                district_addr_temp = ""
                p.extras["third address"] = district_addr3
            else:
                district_addr_temp += " "

        phone = (
            CSS("span#body_FormView3_DISTRICTOFFICEPHONELabel")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        if phone == "504-83POLLY (837-6559)":
            phone = "(504) 837-6559"
        else:
            phone = re.search(r"(\(\d{3}\)\s?\d{3}-\d{4})(.+)?", phone).groups()[0]
        p.district_office.voice = phone

        try:
            phone2 = (
                CSS("span#body_FormView3_DISTRICTOFFICEPHONE2Label")
                .match_one(self.root)
                .text_content()
                .strip()
            )
            if phone2 != "":
                phone2 = re.search(r"(\(\d{3}\)\s?\d{3}-\d{4})(.+)?", phone2).groups()[
                    0
                ]
                p.extras["second phone"] = phone2
        except SelectorError:
            pass

        fax = (
            CSS("span#body_FormView3_FAXNUMBERLabel")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        if fax != "":
            p.district_office.fax = fax

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
