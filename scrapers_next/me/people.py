from spatula import (
    URL,
    CSS,
    HtmlListPage,
    HtmlPage,
    XPath,
    SelectorError,
    ExcelListPage,
)
from dataclasses import dataclass
from openstates.models import ScrapePerson
import re


@dataclass
class PartialPerson:
    name: str
    party: str
    source: str


# is this correct?
_party_map = {
    "D": "Democratic",
    "R": "Republican",
    "I": "Independent",
    "L": "Libertarian",
    "Passamaquoddy Tribe": "Independent",
}


class RepDetail(HtmlPage):
    input_type = PartialPerson

    def process_page(self):
        district = (
            XPath("//*[@id='main-info']/p/span[contains(text(), 'District')]")
            .match_one(self.root)
            .getnext()
        )
        district = XPath("text()").match(district)[0].strip()
        # https://legislature.maine.gov/house/house/MemberProfiles/Details/1193 has no district
        if district != "":
            district = re.search(r"(\d+)\s+-", district).groups()[0]

        p = ScrapePerson(
            name=self.input.name,
            state="me",
            chamber="lower",
            district=district,
            party=self.input.party,
        )

        p.add_source(self.input.source)
        p.add_source(self.source.url)
        p.add_link(self.source.url, note="homepage")

        img = CSS("img.drop-shadow").match_one(self.root).get("src")
        p.image = img

        email = CSS("div#main-info p a").match(self.root)[0].text_content().strip()
        p.email = email

        distr_addr = CSS("div#main-info p br").match(self.root)[0].tail.strip()
        p.district_office.address = distr_addr

        try:
            work_phone = (
                XPath("//*[@id='main-info']/p/span[contains(text(), 'Work')]")
                .match_one(self.root)
                .getnext()
            )
            work_phone = work_phone.text_content().strip()
            p.district_office.voice = work_phone
        except SelectorError:
            pass

        try:
            cell_phone = (
                XPath("//*[@id='main-info']/p/span[contains(text(), 'Cell')]")
                .match_one(self.root)
                .getnext()
            )
            cell_phone = cell_phone.text_content().strip()
            p.extras["Cell Phone"] = cell_phone
        except SelectorError:
            pass

        try:
            home_phone = (
                XPath("//*[@id='main-info']/p/span[contains(text(), 'Home')]")
                .match_one(self.root)
                .getnext()
            )
            home_phone = home_phone.text_content().strip()
            p.extras["Home Phone"] = home_phone
        except SelectorError:
            pass

        seat_no = (
            XPath("//*[@id='main-info']/p/span[contains(text(), 'Seat')]")
            .match_one(self.root)
            .getnext()
        )
        seat_no = seat_no.text_content().strip()
        p.extras["Seat Number"] = seat_no

        towns = (
            XPath("//*[@id='main-info']/p/span[contains(text(), 'Town(s)')]")
            .match_one(self.root)
            .getnext()
        )
        towns = XPath("text()").match(towns)
        if len(towns) > 0 and towns[0].strip() != "":
            p.extras["towns represented"] = []
            for town in towns:
                p.extras["towns represented"] += [town.strip()]

        cap_addr = XPath(
            "//*[@id='welcome']/div/div[1]/div/div/table/tbody/tr[3]/td[2]/text()"
        ).match(self.root)
        capitol_address = ""
        for line in cap_addr:
            capitol_address += line.strip()
            capitol_address += " "
        p.capitol_office.address = capitol_address.strip()

        # education
        try:
            occupation = (
                XPath(
                    "//*[@id='welcome']/div/div[1]/div/div/table/tbody/tr/td[contains(text(), 'Occupation')]"
                )
                .match_one(self.root)
                .getnext()
            )
            p.extras["occupation"] = occupation.text_content().strip()
        except SelectorError:
            pass

        try:
            if (
                XPath(
                    "//*[@id='welcome']/div/div[1]/div/div/table/tbody/tr/td[contains(text(), 'Education')]"
                )
                .match_one(self.root)
                .getnext()
                is not None
            ):
                education = (
                    XPath(
                        "//*[@id='welcome']/div/div[1]/div/div/table/tbody/tr/td[contains(text(), 'Education')]"
                    )
                    .match_one(self.root)
                    .getnext()
                )
                p.extras["education"] = education.text_content().strip()
        except SelectorError:
            pass

        return p


class House(HtmlListPage):
    source = URL("https://legislature.maine.gov/house/house/MemberProfiles/ListAlpha")
    selector = CSS("table tr td", num_items=152)

    def process_item(self, item):
        name_dirty = CSS("br").match(item)[0].tail.strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("br").match(item)[2].tail.strip()
        if re.search(r"\(([A-Z])\s-(.+)", party):
            party = re.search(r"\(([A-Z])\s-(.+)", party).groups()[0]
        party = _party_map[party]

        partial = PartialPerson(name=name, party=party, source=self.source.url)

        detail_link = CSS("a").match(item)[1].get("href")
        # Justin Fecteau resigned 7/4/21
        if (
            detail_link
            == "https://legislature.maine.gov/house/house/MemberProfiles/Details/1361"
        ):
            self.skip()

        return RepDetail(partial, source=detail_link)


class SenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("div#content p img").match_one(self.root).get("src")
        p.image = img

        return p


class Senate(ExcelListPage):
    source = URL(
        "https://legislature.maine.gov/uploads/visual_edit/130th-senate-contact-information-as-of-31221.xlsx"
    )

    def process_item(self, item):
        # skip header and empty rows
        if item[0] == "Dist" or item[0] is None:
            self.skip()

        first_name = item[3]
        last_name = item[4]
        name = first_name + " " + last_name
        district = item[0]
        party = item[2]

        p = ScrapePerson(
            name=name,
            state="me",
            chamber="upper",
            district=district,
            party=party,
        )

        detail_link = URL(f"https://legislature.maine.gov/District-{district}")
        p.add_source(self.source.url)
        p.add_source(detail_link.url)
        p.add_link(detail_link.url, note="homepage")

        county = item[1]
        p.extras["county represented"] = county

        mailing_address = item[5]
        city = item[6]
        zip = item[8]
        address = mailing_address + " " + city + ", ME " + zip
        p.extras["Mailing address"] = address
        # should this be a district office?

        phone = item[9]
        # append area code to phone?
        p.extras["phone"] = phone

        alternate = item[10]
        if alternate is not None:
            p.extras["alternate phone"] = alternate

        email = item[11]
        p.email = email

        return SenDetail(p, source=detail_link)
