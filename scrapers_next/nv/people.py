from spatula import URL, CSS, HtmlListPage, XPath
from openstates.models import ScrapePerson
import re


class Legislators(HtmlListPage):
    selector = CSS("tbody tr.thisRow.listRow")

    def process_item(self, item):
        name_title = XPath("//td[2]/span/a/text()").match(item)
        name = name_title[0]

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

        p.add_source(self.source.url)

        return p


class Senate(Legislators):
    source = URL("https://www.leg.state.nv.us/App/Legislator/A/Senate/Current")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.leg.state.nv.us/App/Legislator/A/Assembly/Current")
    chamber = "lower"
