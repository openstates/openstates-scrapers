# import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    example_source = "https://www.arkleg.state.ar.us/Legislators/Detail?member=B.+Ballinger&ddBienniumSession=2021%2F2021S1"
    # example_source = f"https://www.arkleg.state.ar.us/Legislators/Detail?member=Beckham&ddBienniumSession=2021%2F2021S1"

    def process_page(self):
        # start going through the table now
        # print("hello")

        table_div = CSS(".col-md-7").match(self.root)[0]
        # print(table_div.getchildren())
        # for thing in table_div.getchildren():
        #     print(thing.text_content())

        # for div in table_div.getchildren():
        #     print("this is a div", div.text_content().strip())
        #     print("TEXT", div.text_content().split(": "))
        # print("type: ", type)
        # print("info: ", info)

        # a bunch of rows
        rows = CSS(".row").match(table_div)

        # for each row
        # TODO: party
        party = ""
        name_party = CSS("h1").match_one(self.root).text_content()
        # print("name party", name_party)
        # if re.search("(R)", name_party):
        #     party == "Republican"

        if name_party.endswith("(R)"):
            party = "Republican"
        elif name_party.endswith("(D)"):
            party = "Democrat"
        elif name_party.endswith("(I)"):
            party = "Independent"
        elif name_party.endswith("(G)"):
            party = "Green"
        # print("Party", party)

        image = CSS(".MemberPhoto").match_one(self.root).get("src")
        # print("image", image)

        # phone = (
        #     email
        # ) = (
        #     district
        # ) = (
        #     seniority
        # ) = occupation = religion = veteran = public_service = biography = ""

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
            # for extras, make a separate table?
            # should be able to do "District:": ""
        }
        for row in rows:
            try:
                type = CSS(".col-md-3").match_one(row).text_content()
                info = CSS(".col-md-9").match_one(row).text_content().strip()
                if type == "Biography:":
                    info = CSS(".col-md-9 a").match_one(row).get("href")
                    # print("BIOGRAPHY: ", info)
                if type in table:
                    table[type] = info
                    # print("dictionary", table)
            except SelectorError:
                pass

        # print("here it is: ", table["Phone:"])

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
            p.add_link(table["Biography:"])
            # print("BIOGRAPHY SHOULD BE ADDED")

        # for every key-value pair in table that isn't phone, email, district
        for key in table:
            # print("KEY", key)
            if (
                key == "Phone:"
                or key == "Email:"
                or key == "District:"
                or key == "Biography:"
            ):
                # print("***phone, email, or district here")
                continue
            elif table[key] != "":
                # remove colon at the end
                # print("about to add to extras***")
                # text[:-1]
                p.extras[key[:-1].lower()] = table[key]

        address = CSS(".col-md-12 p b").match_one(self.root).text_content()
        full_address = address[:-5] + "AR " + address[-5:]

        p.add_source(self.source.url)
        p.add_source(self.input.url)
        p.district_office.address = full_address

        return p


class LegList(HtmlListPage):
    source = "https://www.arkleg.state.ar.us/Legislators/List?sort=Type&by=desc&ddBienniumSession=2021%2F2021S1#SearchResults"

    def process_item(self, item):
        # name
        # print("item", item.text_content().replace("\r\n","").replace("                                        ", ""))
        # print("url", item.get("href"))
        # print("ORIGIAL", item.text_content())
        # yall make this bottom better
        # print("just all with the split: ", item.text_content().replace("\r\n","").strip().replace("                                        ", "   ").split("   "))
        chamber_name = (
            item.text_content()
            .replace("\r\n", "")
            .strip()
            .replace("                                        ", "   ")
            .split("   ")
        )
        chamber = chamber_name[0]
        name = chamber_name[1].replace("  ", " ")
        # chamber = XPath("/html//div[@class='row']//div[@class='gridcell']")
        # print(hi)
        if chamber == "Senator":
            chamber = "upper"
        elif chamber == "Representative":
            chamber = "lower"
        # print("children", item.getchildren())
        # source = XPath("//a[contains(@href, 'Detail?')]").match_one(item.getchildren()).get("href")
        source = item.getchildren()[0].get("href")
        p = PartialMember(name=name, chamber=chamber, url=self.source.url)

        return LegDetail(p, source=source)


class PeopleList(LegList):
    # selector = XPath(
    #     "//a[contains(@href, 'Detail?')]",
    # )
    # selector = XPath("/html//div[@class='row']//div[@class='container']//div[@class='col-sm-6 col-md-6']")

    selector = XPath("//div[@class='col-sm-6 col-md-6']")

    # //*[@id="bodyContent"]/div[2]/div[3]/div[1]
    # if XPath("")
    # chamber = "upper"


class SenList(LegList):
    selector = XPath(
        "//a[contains(@href, 'Detail?')][position()<35]",
        num_items=35,
    )
    # /html/body/div[3]/div/main/div/div[1]/div[2]/div[3]
    # /html/body/div[3]/div/main/div/div[1]/div[2]/div[3]/div[1]/a[1]
    # source = "https://senate.arkansas.gov/senators/"
    chamber = "upper"


# /html/body/table/tbody/tr[6]/td/table/tbody/tr/td[2]/p[2]/b[1]/a


class RepList(LegList):
    selector = XPath(
        "/html//div[@class='row tableRow']//a[contains(@href, 'Detail')][position()>35]"
    )
    # source = "https://www.arkansashouse.org/representatives/members"
    chamber = "lower"
