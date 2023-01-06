import attr
import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapePerson


def get_field(field):
    if field.endswith(":"):
        return field[:-1]
    else:
        return field


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    party: str = ""
    email: str = ""
    chamber: str = ""


class NewDetailFieldEncountered(BaseException):
    pass


class LegDetail(HtmlPage):
    input_type = PartialMember

    example_source = (
        "https://www.legis.iowa.gov/legislators/legislator?ga=89&personID=906"
    )

    def process_page(self):

        image = XPath("//img[contains(@src, '/photo')]").match_one(self.root).get("src")

        p = ScrapePerson(
            name=self.input.name,
            state="ia",
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=self.input.email,
            image=image,
        )
        p.add_source(self.source.url)
        p.add_source(self.input.url)

        try:
            for link in CSS(".link_list a").match(self.root):
                url = link.get("href")
                if "leaving?" in url:
                    url = url.replace("https://www.legis.iowa.gov/leaving?forward=", "")
                if not url.startswith("http://") or not url.startswith("https://"):
                    url = f"http://{url}"
                p.add_link(url)
        except SelectorError:
            pass

        other_info = XPath("//div[@class='legisIndent divideVert']//table").match(
            self.root
        )[0]

        if len(other_info.getchildren()) > 1:
            info_rows = XPath("//tr").match(other_info)
            for row in info_rows:
                if len(row) > 1:
                    raw_field_name = row[0].text_content().strip().lower()
                    field_name = re.sub(":", "", raw_field_name)
                    field_text = row[1].text_content().strip()

                    extra_fields = {
                        "home email",
                        "home phone",
                        "business phone",
                        "occupation",
                        "service began",
                        "home address",
                        "other phone",
                        "business address",
                        "cell phone",
                    }

                    if field_name == "legislative email":
                        p.email = field_text.lower()
                    elif field_name == "capitol phone":
                        p.capitol_office.voice = field_text
                    elif field_name == "office phone":
                        p.district_office.voice = field_text
                    elif field_name in extra_fields:
                        p.extras[field_name] = field_text
                    else:
                        raise NewDetailFieldEncountered

        return p


class LegList(HtmlListPage):
    selector = CSS("#sortableTable tbody tr")

    def process_item(self, item):

        __, name, district, party, county, email = item.getchildren()
        url = CSS("a").match(item)[0].get("href")

        p = PartialMember(
            name=name.text_content(),
            chamber=self.chamber,
            party=party.text_content(),
            district=district.text_content(),
            email=email.text_content(),
            url=self.source.url,
        )

        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.legis.iowa.gov/legislators/senate"
    chamber = "upper"


class RepList(LegList):
    source = "https://www.legis.iowa.gov/legislators/house"
    chamber = "lower"
