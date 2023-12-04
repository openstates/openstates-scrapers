from spatula import (
    URL,
    CSS,
    HtmlListPage,
    HtmlPage,
    XPath,
    SelectorError,
    ExcelListPage,
    SkipItem,
)
from dataclasses import dataclass
from openstates.models import ScrapePerson
import re


@dataclass
class PartialPerson:
    name: str
    party: str
    source: str


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
            district = district
        else:
            raise SkipItem("non-voting member")

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

        try:
            email = CSS("div#main-info p a").match(self.root)[0].text_content().strip()
            p.email = email
        except SelectorError:
            return

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
            education = (
                XPath(
                    "//*[@id='welcome']/div/div[1]/div/div/table/tbody/tr/td[contains(text(), 'Education')]"
                )
                .match_one(self.root)
                .getnext()
            )
            if education is not None:
                p.extras["education"] = education.text_content().strip()
        except SelectorError:
            pass

        return p


class House(HtmlListPage):
    source = URL("https://legislature.maine.gov/house/house/MemberProfiles/ListAlpha")
    selector = CSS("table tr td", min_items=152)
    party_re = re.compile(r"\(([A-Z])\s-(.+)")

    def process_item(self, item):
        name_dirty = CSS("br").match(item)[0].tail.strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("br").match(item)[2].tail.strip()
        if self.party_re.search(party):
            party = self.party_re.search(party).groups()[0]
        party = _party_map[party]

        partial = PartialPerson(name=name, party=party, source=self.source.url)

        detail_link = CSS("a").match(item)[1].get("href")
        # Justin Fecteau resigned 7/4/21
        if (
            detail_link
            == "https://legislature.maine.gov/house/house/MemberProfiles/Details/1361"
        ):
            self.skip()

        return RepDetail(partial, source=URL(detail_link, timeout=30))


class SenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        # some Senators don't have images
        try:
            img = CSS("div#content p img").match_one(self.root).get("src")
        except Exception:
            img = ""
        p.image = img

        if self.source.url == "https://legislature.maine.gov/District-22":
            addr = CSS("div#content p strong").match(self.root)[2].tail.strip()
        else:
            addr = (
                CSS("div#content p strong")
                .match(self.root)[1]
                .tail.strip()
                .lstrip(":")
                .strip()
            )
        if addr != p.district_office.address:
            p.extras["Additional address"] = addr

        try:
            state_phone = (
                XPath("//*[@id='content']/p/strong[contains(text(), 'State')]")
                .match_one(self.root)
                .tail.strip()
            )
            state_phone = state_phone.lstrip(":").strip()
            p.capitol_office.voice = state_phone
        except SelectorError:
            pass

        try:
            state_phone = (
                XPath("//*[@id='content']/p/b[contains(text(), 'State')]")
                .match_one(self.root)
                .tail.strip()
            )
            state_phone = state_phone.lstrip(":").strip()
            p.capitol_office.voice = state_phone
        except SelectorError:
            pass

        website = (
            XPath("//*[@id='content']/p/strong[contains(text(), 'Website')]")
            .match_one(self.root)
            .getnext()
        )
        if website.get("href") is None:
            website = website.getnext().get("href")
        else:
            website = website.get("href")
        p.add_link(website, note="website")

        return p


class Senate(ExcelListPage):
    source = URL(
        "https://legislature.maine.gov/uploads/visual_edit/131-senator-contact-information-2.xlsx"
    )

    def process_item(self, item):
        # skip header and empty rows
        if item[0] == "Dist" or item[0] is None:
            self.skip()

        first_name = item[2].strip()
        last_name = item[3].strip()
        name = first_name + " " + last_name
        district = item[0]
        party = item[1].strip()
        print(f"name: {name} district: {district} party: {party}")

        if not district:
            # non voting members ignored for now
            raise SkipItem(f"not voting member {name}")

        p = ScrapePerson(
            name=name,
            state="me",
            chamber="upper",
            district=district,
            party=party,
        )

        p.given_name = first_name
        p.family_name = last_name

        detail_link = URL(f"https://legislature.maine.gov/District{district}")
        p.add_source(self.source.url)
        p.add_source(detail_link.url)
        p.add_link(detail_link.url, note="homepage")

        # county = item[1].strip()
        # p.extras["county represented"] = county

        mailing_address = item[4].strip()
        zipcode = item[7].strip()
        city = item[5].strip()
        address = f"{mailing_address}, {city}, ME {zipcode}"
        if re.search(r"St(\s|,)", address):
            address = re.sub(r"St\s", "Street ", address)
            address = re.sub(r"St,", "Street,", address)
        if re.search(r"PO\s", address):
            address = re.sub(r"PO\s", "P.O. ", address)
        if re.search(r"Saint\s", address):
            address = re.sub(r"Saint\s", "St. ", address)
        if re.search(r"N\.", address):
            address = re.sub(r"N\.", "North", address)
        p.district_office.address = address

        # phone = item[9].strip()
        # phone = "(207) " + phone
        # p.district_office.voice = phone

        # alternate = item[10]
        # if alternate is not None:
        #     p.extras["alternate phone"] = alternate.strip()

        email = item[8].strip()
        p.email = email

        return SenDetail(p, source=detail_link)
