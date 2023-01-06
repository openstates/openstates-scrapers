import attr
from spatula import HtmlListPage, HtmlPage, URL, CSS, ExcelListPage
from openstates.models import ScrapePerson

PARTIES = {"D": "Democratic", "R": "Republican"}


@attr.s(auto_attribs=True)
class HousePartial:
    last_name: str
    first_name: str
    district: int
    hometown: str
    party: str
    voice: str
    room: str
    url: str


class Representatives(HtmlListPage):
    # note: there is a CSV, but it requires a bunch of ASP.net hoops to actually get
    source = URL(
        "https://house.mo.gov/MemberGridCluster.aspx?year=2023&code=R+&filter=clear"
    )
    selector = CSS("tr")

    def process_item(self, item):
        tds = CSS("td").match(item, min_items=0, max_items=8)
        if not tds:
            self.skip()
        _, last, first, district, party, town, phone, room = tds
        if last.text_content() == "Vacant":
            self.skip()
        return HouseDetail(
            HousePartial(
                last_name=last.text_content(),
                first_name=first.text_content(),
                district=int(district.text_content()),
                party=party.text_content(),
                hometown=town.text_content().strip(),
                voice=phone.text_content(),
                room=room.text_content(),
                url=CSS("a").match_one(last).get("href"),
            )
        )


class HouseDetail(HtmlPage):
    input_type = HousePartial

    def get_source_from_input(self):
        return self.input.url

    def process_page(self):
        party = PARTIES[self.input.party]

        photo = CSS("img#ContentPlaceHolder1_imgPhoto1").match_one(self.root).get("src")

        p = ScrapePerson(
            state="mo",
            party=party,
            image=photo,
            chamber="lower",
            district=self.input.district,
            name=f"{self.input.first_name} {self.input.last_name}",
            given_name=self.input.first_name,
            family_name=self.input.last_name,
        )
        p.extras["hometown"] = self.input.hometown
        p.capitol_office.voice = self.input.voice
        p.capitol_office.address = (
            "MO House of Representatives; 201 West Capitol Avenue; "
            f"Room {self.input.room}; Jefferson City MO 65101 "
        )
        p.add_link(self.input.url)
        p.add_source(self.input.url)
        return p


class Senators(ExcelListPage):
    source = "https://www.senate.mo.gov/21info/2021Sens.xlsx"
    HEADERS = ("District", "First Name", "Last Name", "Address", "Party", "Phone")

    def process_item(self, row):
        if row == self.HEADERS:
            self.skip("header row")
        else:
            row = dict(zip(self.HEADERS, row))

        name = f"{row['First Name']} {row['Last Name']}"
        p = ScrapePerson(
            name=name,
            state="mo",
            chamber="upper",
            district=row["District"],
            given_name=row["First Name"],
            family_name=row["Last Name"],
            party=PARTIES[row["Party"]],
        )
        p.capitol_office.address = row["Address"]
        p.capitol_office.voice = row["Phone"]
        return p
