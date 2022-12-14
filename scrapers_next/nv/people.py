from spatula import URL, CSS, HtmlListPage, XPath, SkipItem
from openstates.models import ScrapePerson
import re


class NewDetailFieldEncountered(BaseException):
    pass


class Legislators(HtmlListPage):
    selector = CSS("tbody tr.thisRow.listRow")
    field_names = set()

    def process_item(self, item):
        name_title = XPath(".//td/span/a/text()").match(item)
        name_dirty = name_title[0].split(", ")
        if name_dirty[0] == "Vacant":
            raise SkipItem("vacant")
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("td a").match(item)[2].text_content().strip()
        district = CSS("td a").match(item)[3].text_content().strip()
        district = re.search(r"No\.\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="nv",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        if len(name_title) > 1:
            title = name_title[1]
            p.extras["title"] = title

        detail_link = CSS("td span a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        img = CSS("img").match_one(item).get("src")
        p.image = img

        extra_info = item.getnext()
        district_addr = CSS("td").match(extra_info)[0].text_content().strip()
        p.district_office.address = district_addr

        extra_details = CSS("td div div div span.fieldName").match(extra_info)

        for detail_field in extra_details:
            field_name = detail_field.text_content().strip().lower()
            field_text = detail_field.getnext().text_content().strip().lower()
            if "email" in field_name:
                p.email = field_text
            elif "leg bldg room" in field_name:
                chambers = {"upper": "Senate", "lower": "Assembly"}
                cap_addr = (
                    f"Room {field_text};"
                    f"c/o Nevada {chambers[self.chamber]};"
                    "401 South Carson Street;"
                    "Carson City, NV 89701-4747"
                )
                p.capitol_office.address = cap_addr
            elif "leg bldg phone" in field_name:
                p.capitol_office.voice = field_text
            elif "work phone" in field_name:
                p.district_office.voice = field_text
            elif "fax" in field_name:
                p.district_office.fax = field_text
            elif "term ends" in field_name:
                pass
            else:
                raise NewDetailFieldEncountered

        return p


class Senate(Legislators):
    source = URL("https://www.leg.state.nv.us/App/Legislator/A/Senate/Current")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.leg.state.nv.us/App/Legislator/A/Assembly/Current")
    chamber = "lower"
