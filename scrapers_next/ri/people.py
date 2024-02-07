from spatula import HtmlListPage, CSS, XPath, HtmlPage, Page, URL
from openstates.models import ScrapePerson
import xlrd
import re

# Regex patterns to fix specific bad urls provided for new member bio pages
#  TODO: Check at future point in 2023 session if these urls still bad,
#   or if regex string substitution fix can be removed from LegList
mary_shallcross_re = re.compile("shallcrosssmith/")
cruz_re = re.compile("delacruz/")

EXCEL_URL = URL(
    "https://www.rilegislature.gov/SiteAssets/Representatives.xls",
    timeout=30,
)


class LegacyExcelPage(Page):
    """
    RI party and addresses are listed in separate excel files.
    """

    def postprocess_response(self) -> None:
        wb = xlrd.open_workbook(file_contents=self.response.content)
        self.worksheet = wb.sheet_by_index(0)

    def process_page(self):
        mapping = {}
        for rownum in range(1, self.worksheet.nrows):
            row_vals = self.worksheet.row_values(rownum)
            _district = int(row_vals[0])
            city_town = row_vals[1]
            _name = row_vals[2]
            party = row_vals[3]
            office_addr = row_vals[4]
            _email = row_vals[5]

            mapping[_district] = (_email, city_town, _name, party, office_addr)

        return mapping


class Image(HtmlPage):
    input_type = ScrapePerson

    def process_page(self):
        images = self.root.cssselect("img")
        image = images[2]
        image = image.get("src")

        self.input.image = image

        return self.input


class LegList(HtmlListPage):
    def process_item(self, item):
        name = CSS("td").match(item)[1].text_content().strip().split(" ", 1)
        # Splitting name to take off Senator/Rep. from beginning
        name = name[1]
        district = CSS("td").match(item)[0].text_content()
        email = CSS("td").match(item)[2].text_content()
        phone = CSS("td").match(item)[3].text_content()

        _email, city_town, _name, party, office_addr = self.detail_mapping[
            int(district)
        ]

        if party == "Democrat":
            party = "Democratic"

        p = ScrapePerson(
            name=name,
            state="ri",
            party=party,
            district=district,
            chamber=self.chamber,
        )

        p.extras["City/Town Represented"] = city_town
        p.district_office.address = office_addr
        # skip invalid phone numbers
        if "401" in phone:
            p.district_office.voice = phone

        bio = CSS("td center a").match_one(item).get("href")

        # Fixes bio page bad urls for Rep Shallcross, Sen Cruz
        bio = mary_shallcross_re.sub("shallcross%20smith/", bio)
        bio = cruz_re.sub("de%20la%20Cruz/", bio)

        p.email = email
        p.add_link(bio)
        p.add_source(self.source.url, note="Contact Web Page")
        p.add_source(EXCEL_URL.url, note="Detail Excel Source")
        p.add_source(bio, note="Image Source")

        return Image(p, source=bio)


class AssemblyList(LegList):
    source = URL(
        "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp", timeout=30
    )
    selector = XPath("//tr[@valign='TOP']", num_items=75)
    chamber = "lower"
    dependencies = {
        "detail_mapping": LegacyExcelPage(
            source=EXCEL_URL,
        )
    }


class SenList(LegList):
    source = URL(
        "http://webserver.rilegislature.gov/Email/SenEmailListDistrict.asp", timeout=30
    )
    selector = XPath("//tr[@valign='TOP']", num_items=38)
    chamber = "upper"
    dependencies = {
        "detail_mapping": LegacyExcelPage(
            source=URL(
                "https://www.rilegislature.gov/SiteAssets/Senators.xls",
                timeout=30,
            )
        )
    }
