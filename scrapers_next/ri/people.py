from spatula import HtmlListPage, CSS, XPath, HtmlPage, Page
from openstates.models import ScrapePerson
import xlrd


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
        p.district_office.voice = phone

        bio = CSS("td center a").match_one(item).get("href")

        p.email = email
        p.add_link(bio)
        p.add_source(self.source.url, note="Contact Web Page")
        p.add_source(
            self.dependencies["detail_mapping"].source.url, note="Detail Excel Source"
        )
        p.add_source(bio, note="Image Source")

        return Image(p, source=bio)


class AssemblyList(LegList):
    source = "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=75)
    chamber = "lower"
    dependencies = {
        "detail_mapping": LegacyExcelPage(
            source="http://www.rilegislature.gov/SiteAssets/MailingLists/Representatives.xls"
        )
    }


class SenList(LegList):
    source = "http://webserver.rilegislature.gov/Email/SenEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=38)
    chamber = "upper"
    dependencies = {
        "detail_mapping": LegacyExcelPage(
            source="http://www.rilegislature.gov/SiteAssets/MailingLists/Senators.xls"
        )
    }
