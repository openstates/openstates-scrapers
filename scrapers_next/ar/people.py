import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    #example_source = "https://www.arkleg.state.ar.us/Legislators/Detail?member=B.+Ballinger&ddBienniumSession=2023%2F2023S1"

    def process_page(self):

        table_div = CSS(".col-md-7").match(self.root)[0]

        rows = CSS(".row").match(table_div)

        party = ""
        name_party = CSS("h1").match_one(self.root).text_content()

        if name_party.endswith("(R)"):
            party = "Republican"
        elif name_party.endswith("(D)"):
            party = "Democrat"
        elif name_party.endswith("(I)"):
            party = "Independent"
        elif name_party.endswith("(G)"):
            party = "Green"

        image = CSS(".MemberPhoto").match_one(self.root).get("src")

        table = {
            "Phone:": "",
            "Email:": "",
            "District:": "",
            "Seniority:": "",
            "Occupation:": "",
            "Church Affiliation:": "",
            "Veteran:": "",
            "Public Service:": "",
            "Biography:": "",
        }

        for row in rows:
            try:
                type = CSS(".col-md-3").match_one(row).text_content()
                info = CSS(".col-md-9").match_one(row).text_content().strip()
                if type == "Biography:":
                    info = CSS(".col-md-9 a").match_one(row).get("href")
                if type in table:
                    table[type] = info
            except SelectorError:
                pass

        p = ScrapePerson(
            name=self.input.name,
            state="ar",
            chamber=self.input.chamber,
            party=party,
            image=image,
            district=table["District:"],
            email=table["Email:"],
        )

        if table["Biography:"] != "":
            p.add_link(table["Biography:"], "Biography")

        for key in table:
            if (
                key == "Phone:"
                or key == "Email:"
                or key == "District:"
                or key == "Biography:"
            ):
                continue
            elif table[key] != "":
                # remove the colon at the end
                p.extras[key[:-1].lower()] = table[key]

        address = CSS(".col-md-12 p b").match_one(self.root).text_content()
        full_address = address[:-5] + "AR " + address[-5:]

        p.add_source(self.source.url)
        p.add_source(self.input.url)
        p.district_office.address = full_address

        return p


class LegList(HtmlListPage):
    source = "https://www.arkleg.state.ar.us/Legislators/List?sort=Type&by=desc&ddBienniumSession=2023%2F2023S1#SearchResults"
    selector = XPath(
        "//div[@role='grid']//div[contains(@class, 'row')]//div[@class='col-md-6']"
    )
    # contains(@class, 'measure-tab')
    # selector = XPath("//div[@class='row tableRow']")
    # selector = CSS("row tableRow")
    # selector = XPath('//div[@class="row tableRow"]')

    def process_item(self, item):
        chamber_name = (
            item.text_content()
            .replace("\r\n", "")
            .strip()
            .replace("                                        ", "   ")
            .split("   ")
        )

        chamber = chamber_name[0]

        name = chamber_name[1].replace("  ", " ")
        if "(Resigned)" in name:
            self.skip()

        if chamber == "Senator":
            chamber = "upper"
        elif chamber == "Representative":
            chamber = "lower"

        source = item.getchildren()[0].get("href")
        p = PartialMember(name=name, chamber=chamber, url=self.source.url)

        return LegDetail(p, source=source)
