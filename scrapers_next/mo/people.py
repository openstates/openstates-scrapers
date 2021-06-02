import attr
from spatula import HtmlListPage, HtmlPage, URL, CSS
from ..common.people import Person, PeopleWorkflow


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


class HouseList(HtmlListPage):
    # note: there is a CSV, but it requires a bunch of ASP.net hoops to actually get
    source = URL(
        "https://house.mo.gov/MemberGridCluster.aspx?year=2021&code=R+&filter=clear"
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

    def process_page(self):
        party = {"D": "Democratic", "R": "Republican"}[self.input.party]

        photo = CSS("img#ContentPlaceHolder1_imgPhoto1").match_one(self.root).get("src")

        p = Person(
            state="mo",
            party=party,
            image=photo,
            chamber="lower",
            district=self.input.district,
            name=f"{self.input.first_name} {self.input.last_name}",
            given_name=self.input.first_name,
            family_name=self.input.last_name,
        )
        # TODO
        # p.extras["hometown"] = self.input.hometown
        p.capitol_office.voice = self.input.voice
        p.capitol_office.address = (
            "MO House of Representatives; 201 West Capitol Avenue; "
            f"Room {self.input.room}; Jefferson City MO 65101 "
        )
        p.add_link(self.input.url)
        p.add_source(self.input.url)
        return p


house_members = PeopleWorkflow(HouseList)
