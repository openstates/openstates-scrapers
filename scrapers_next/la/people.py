from spatula import HtmlListPage, CSS, URL, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegislatorDetail(HtmlPage):
    da_re = re.compile(r"L(A|a)\s\s?\s?\d{5}(-\d{4})?$")
    phone_re = re.compile(r"(\(\d{3}\)\s?\d{3}-\d{4})(.+)?")

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
            if self.da_re.search(district_addr_temp) and not district_addr1:
                district_addr1 = district_addr_temp
                district_addr_temp = ""
                p.district_office.address = district_addr1
            elif self.da_re.search(district_addr_temp) and not district_addr2:
                district_addr2 = district_addr_temp
                district_addr_temp = ""
                p.add_office("district", address=district_addr2)
            elif self.da_re.search(district_addr_temp) and not district_addr3:
                district_addr3 = district_addr_temp
                district_addr_temp = ""
                p.add_office("district", address=district_addr3)
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
            phone = self.phone_re.search(phone)
            if phone:
                phone = phone.groups()[0]
            else:
                phone = ""
        p.district_office.voice = phone

        try:
            phone2 = (
                CSS("span#body_FormView3_DISTRICTOFFICEPHONE2Label")
                .match_one(self.root)
                .text_content()
                .strip()
            )
            if phone2 != "":
                phone2 = self.phone_re.search(phone2).groups()[0]
                p.extras["second phone"] = phone2
        except SelectorError:
            pass

        fax = (
            CSS("span#body_FormView3_FAXNUMBERLabel")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        fax = self.phone_re.search(fax)
        if fax:
            p.district_office.fax = fax.groups()[0]

        leg_assistant = (
            CSS("span#body_FormView6_LEGISLATIVEAIDELabel")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        p.extras["legislative assistant"] = leg_assistant

        parishes = (
            CSS("span#body_FormView6_DISTRICTPARISHESLabel")
            .match_one(self.root)
            .text_content()
            .strip()
            .split(", ")
        )
        p.extras["representing parishes"] = parishes

        education = (
            CSS("span#body_FormView4_EDUCATIONLabel")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        if education != "":
            p.extras["education"] = education

        return p


class SenateLegislators(HtmlListPage):
    selector = CSS("fieldset div.media")

    def process_item(self, item):
        name_dirty = CSS("h4 span").match_one(item).text_content().strip()
        if "Vacant" in name_dirty:
            self.skip("vacant")
        name_dirty = name_dirty.split(", ")
        split_length = len(name_dirty)
        # 3 means something like 'Beaullieu, IV, Gerald "Beau"'
        # also, we can't have more than one comma in a name (per Person model)
        if split_length == 3:
            last_name = f"{name_dirty[0]} {name_dirty[1]}"
            first_name = name_dirty[2]
        # 2 means something like 'Bagley, Larry'
        elif split_length == 2:
            last_name = name_dirty[0]
            first_name = name_dirty[1]
        if any(j in first_name for j in ["Jr", "Jr."]):
            first_name = first_name.split(" ")[0]
            last_name += " Jr."
        name = f"{first_name} {last_name}"

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

        return LegislatorDetail(p, source=URL(detail_link, timeout=30))


class HouseLegislators(HtmlListPage):
    selector = CSS("fieldset div.card-body")

    def process_item(self, item):
        name_dirty = CSS("a").match(item)[0].text_content().strip()
        if "Vacant" in name_dirty:
            self.skip("vacant")
        name_dirty = name_dirty.split(", ")
        split_length = len(name_dirty)
        # 3 means something like 'Beaullieu, IV, Gerald "Beau"'
        # also, we can't have more than one comma in a name (per Person model)
        if split_length == 3:
            last_name = f"{name_dirty[0]} {name_dirty[1]}"
            first_name = name_dirty[2]
        # 2 means something like 'Bagley, Larry'
        elif split_length == 2:
            last_name = name_dirty[0]
            first_name = name_dirty[1]
        if any(j in first_name for j in ["Jr", "Jr."]):
            first_name = first_name.split(" ")[0]
            last_name += " Jr."
        name = f"{first_name} {last_name}"

        district = (
            CSS("p i.fa-solid.fa-map").match_one(item).getnext().text_content().strip()
        )
        party = (
            CSS("p i.fa-solid.fa-user").match_one(item).getnext().text_content().strip()
        )
        if party == "Democrat":
            party = "Democratic"
        email = CSS("a").match(item)[1].text_content().strip()
        img = (
            item.getprevious()
            .getprevious()
            .getchildren()[0]
            .getchildren()[0]
            .getchildren()[0]
            .get("src")
        )

        p = ScrapePerson(
            name=name,
            state="la",
            party=party,
            district=district,
            chamber=self.chamber,
            email=email,
            image=img,
        )

        detail_link = CSS("a").match(item)[0].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegislatorDetail(p, source=URL(detail_link, timeout=30))


class Senate(SenateLegislators):
    source = URL("https://senate.la.gov/Senators_FullInfo", timeout=30)
    chamber = "upper"


class House(HouseLegislators):
    source = URL("https://house.louisiana.gov/H_Reps/H_Reps_FullInfo", timeout=30)
    chamber = "lower"
