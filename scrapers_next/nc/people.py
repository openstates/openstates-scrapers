import attr

# import re
from spatula import HtmlListPage, HtmlPage, CSS

# from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    party: str = ""
    # email: str = ""
    chamber: str = ""
    counties: str = ""


class LegDetail(HtmlPage):
    input_type = PartialMember

    example_source = "https://www.ncleg.gov/Members/Biography/S/416"

    # def get_field(self, field):
    #     if field.endswith(":"):
    #         return field[:-1]
    #     else:
    #         return field

    def process_page(self):

        image = ("//img[contains(@src, '/photo')]").match_one(self.root).get("src")
        print(image)
        # p = ScrapePerson(
        #     name=self.input.name,
        #     state="nc",
        #     chamber=self.input.chamber,
        #     party=self.input.party,
        #     district=self.input.district,
        #     # email=email,
        #     # image=image,
        # )


class LegList(HtmlListPage):
    selector = CSS("#memberTable tbody tr")

    def process_item(self, item):
        # try:
        #     name, district, district2, __, __, __ = CSS(
        #         ".pr-0 p"
        #     ).match(item)
        #     print("Name, district, district 2", name.text_content())
        #     url = name.get("href")

        #     print("URL", url)
        # except ValueError:
        #     name, district, district2, __, __, __, __ = CSS(
        #         ".pr-0 p"
        #     ).match(item)

        party, district, _, _, full_name, counties = item.getchildren()

        party = party.text_content().strip()
        party = dict(D="Democratic", R="Republican")[party]

        # name.text_content(), district.text_content(), counties.text_content()
        # image = CSS("img").match_one(image).get("src")

        # TODO: for full name: Sam Searcy (Resigned 1/6/21) and Sydney Batch

        # TODO: make sure Sam Searcy is skipped?

        # if full_name.text_content().strip()
        # full_name = full_name.text_content()
        print("FULL NAME", full_name.text_content())
        name = full_name.text_content()
        if "Resigned" in full_name.text_content():
            self.skip()
        elif "Appointed" in full_name.text_content():
            name = (
                full_name.text_content()
                .split("(Appointed")[0]
                .replace("\r\n", "")
                .strip()
            )
            print("FULL", full_name)

        p = PartialMember(
            name=name,
            # state="nc",
            party=party,
            district=district.text_content(),
            chamber=self.chamber,
            url=self.source.url,
            counties=counties.text_content()
            .strip()
            .replace("\r\n", "")
            .replace("\xa0", "")
            .replace("                        ", " ")
            # image=image,
            # email=email.text_content(),
        )

        # p.capitol_office.voice = phone.text_content()
        # p.add_source(self.source.url)
        # p.add_source(url)
        new_source = CSS("a").match_one(full_name)
        print("NEW SOURCE", new_source.get("href"))
        url = new_source.get("href")
        # url = CSS(".sorting_1 a").match(item)
        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/S"
    chamber = "upper"


class RepList(LegList):
    source = "https://www.ncleg.gov/Members/MemberList/H"
    chamber = "lower"
