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
        print("hello")

        table_div = CSS(".col-md-7").match(self.root)[0]
        # print(table_div.getchildren())
        # for thing in table_div.getchildren():
        #     print(thing.text_content())

        for div in table_div.getchildren():
            print("this is a div", div.text_content().strip())
            print("TEXT", div.text_content().split(": "))
            # print("type: ", type)
            # print("info: ", info)

        # a bunch of rows
        rows = CSS(".row").match(table_div)
        # print("rows", rows)
        # second_div = CSS(".d-none").match(rows)
        # for second_div in rows:
        #     print("i see", second_div.text_content())

        # for each row
        # TODO: party
        # TODO: image
        phone = (
            email
        ) = (
            district
        ) = (
            seniority
        ) = occupation = religion = veteran = public_service = biography = ""
        # for row in rows:
        #     try:
        #         type = CSS(".col-md-3").match_one(row).text_content()
        #         print("type", type)
        #         info = CSS(".col-md-9").match_one(row).text_content().strip()
        #         print("info", info)
        #     except SelectorError:
        #         pass
        #     # print("type: ", type.text_content())
        #     # print("info: ", info.text_content())

        #     if type == "Phone:":
        #         # phone number can be empty
        #         phone = info
        #     elif type == "Email:":
        #         email = info
        #     elif type == "District:":
        #         district = info
        #     elif type == "Seniority:":
        #         seniority = info
        #     elif type == "Occupation:":
        #         occupation = info
        #     elif type == "District:":
        #         district = info
        table = {
            "Phone:": phone,
            "Email:": email,
            "District:": district,
            "Seniority:": seniority,
            "Occupation:": occupation,
            "Church Affiliation:": religion,
            "Veteran:": veteran,
            "Public Service:": public_service,
            "Biography:": biography,
        }
        for row in rows:
            try:
                type = CSS(".col-md-3").match_one(row).text_content()
                info = CSS(".col-md-9").match_one(row).text_content().strip()
                if type in table:
                    table[type] = info
                    print("dictionary", table)
            except SelectorError:
                pass

        print("here it is: ", table["Phone:"])

        p = ScrapePerson(
            name=self.input.name,
            state="ar",
            chamber=self.input.chamber,
            # party=party,
            # image=image,
            district=table["District:"],
            email=table["Email:"],
        )

        return p


class LegList(HtmlListPage):
    source = "https://www.arkleg.state.ar.us/Legislators/List?sort=Type&by=desc&ddBienniumSession=2021%2F2021S1#SearchResults"

    def process_item(self, item):
        # name
        print("item", item.text_content())
        print("url", item.get("href"))
        # not best practice to call self.chamber here
        p = PartialMember(
            name=item.text_content(), chamber=self.chamber, url=self.source.url
        )

        return LegDetail(p, source=item.get("href"))


class SenList(LegList):
    selector = XPath(
        "/html//div[@class='row tableRow']//a[contains(@href, 'Detail')][position()<=35]"
    )
    # source = "https://senate.arkansas.gov/senators/"
    chamber = "upper"


class RepList(LegList):
    selector = XPath("//input[@type='image']")
    # source = "https://www.arkansashouse.org/representatives/members"
    chamber = "lower"
