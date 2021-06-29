import lxml.html
from spatula import HtmlListPage, CSS, SelectorError
from ..common.people import ScrapePerson


class BrokenHtmlListPage(HtmlListPage):
    def postprocess_response(self) -> None:
        # this page has a bad comment that makes the entire page parse incorrectly
        fixed_content = self.response.content.replace(b"--!>", b"-->")
        self.root = lxml.html.fromstring(fixed_content)
        if hasattr(self.source, "url"):
            self.root.make_links_absolute(self.source.url)  # type: ignore


class LegList(BrokenHtmlListPage):
    def process_item(self, item):
        try:
            name = CSS("a").match(item)[0].text_content()
        except SelectorError:
            self.skip("header row")

        if "--" in name:
            name = name.split("--")[0].strip()

        _, district, party, email, room, capitol_phone = item.getchildren()

        district = district.text_content()

        party = party.text_content()
        if party == "R":
            party = "Republican"
        elif party == "D":
            party = "Democratic"

        email = email.text_content()
        if email.startswith("Email: "):
            email = email.replace("Email: ", "").lower() + "@azleg.gov"
        else:
            email = ""

        room = room.text_content()
        if self.chamber == "lower":
            address = "House of Representatives\n "
        elif self.chamber == "upper":
            address = "Senate\n "
        address = address + "1700 West Washington\n " + room + "\nPhoenix, AZ 85007"

        capitol_phone = capitol_phone.text_content()

        image = CSS("td a img").match(item)
        if image:
            image = image[0].get("src")

        p = ScrapePerson(
            name=name,
            state="az",
            chamber=self.chamber,
            district=district,
            party=party,
            email=email,
            image=image,
        )

        p.capitol_office.address = address
        p.capitol_office.voice = capitol_phone
        return p


class SenList(LegList):
    source = "https://www.azleg.gov/memberroster/?body=S"
    selector = CSS("table tr")
    chamber = "upper"


class RepList(LegList):
    source = "https://www.azleg.gov/memberroster/?body=H"
    selector = CSS("table tr")
    chamber = "lower"
