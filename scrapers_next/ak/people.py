# import the objects I will need
import attr
from spatula import HtmlPage, HtmlListPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    example_source = "http://www.akleg.gov/basis/Member/Detail/32?code=BCH"

    def process_page(self):

        details_div = CSS(".bioright").match(self.root)[0]

        name_span = CSS(".formal_name").match(details_div)[0].text_content()
        name_list = name_span.split(" ")
        given_name = name_list[1]
        family_name = " ".join(name_list[2:])

        email = CSS("a").match(details_div)[0].text_content().strip()

        div_text = details_div.text_content().replace("\r\n", " ").split(" ")
        # TODO: Write a faster way to get untagged text elements on page
        text_list = [x for x in div_text if len(x)]
        district_index = text_list.index("District:")
        if not district_index == 5:
            print(district_index)

        party = "Democrat"

        p = ScrapePerson(
            name=f"{given_name} {family_name}",
            given_name=given_name,
            family_name=family_name,
            state="ak",
            chamber=self.input.chamber,
            party=party,
            image="",
            district="",
            email=email,
        )

        try:
            leadership_title = (
                CSS(".leadership_title").match(details_div)[0].text_content()
            )
        except SelectorError:
            leadership_title = ""

        p.extras["title"] = leadership_title

        return p


class LegList(HtmlListPage):
    session_num = "32"
    source = f"https://www.akleg.gov/basis/mbr_info.asp?session={session_num}"
    selector = XPath("//html/body/div[2]/div/div/table//tr[position()>1]/td[1]/nobr/a")

    def process_item(self, item):
        title = item.text_content()
        title_list = title.strip().split(" ")
        chamber = title_list[0]

        if chamber == "Senator":
            chamber = "upper"
        elif chamber == "Representative":
            chamber = "lower"

        # print(chamber)
        source = item.get("href")
        # print(source)
        p = PartialMember(chamber=chamber, url=self.source.url)

        return LegDetail(p, source=source)
