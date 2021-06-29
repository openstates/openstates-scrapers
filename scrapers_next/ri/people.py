import re
from spatula import HtmlListPage, CSS, XPath, HtmlPage, Page
from ..common.people import ScrapePerson
import xlrd


class AssemblyExcelPage(Page):
    """
    RI party and addresses are listed in separate excel files.
    """

    source = "http://www.rilegislature.gov/SiteAssets/MailingLists/Representatives.xls"

    def postprocess_response(self) -> None:
        wb = xlrd.open_workbook(file_contents=self.response.content)
        self.worksheet = wb.sheet_by_index(0)

    def process_page(self):
        mapping = {}
        for rownum in range(1, self.worksheet.nrows):
            # for colnum in range(1, self.worksheet.ncols):
            row_vals = self.worksheet.row_values(rownum)
            _district = int(row_vals[0])
            city_town = row_vals[1]
            _name = row_vals[2]
            party = row_vals[3]
            office_addr = row_vals[4]
            _email = row_vals[5]

            mapping[_district] = (_email, city_town, _name, party, office_addr)

        return mapping


class SenExcelPage(Page):
    """
    RI party and addresses are listed in separate excel files.
    """

    source = "http://www.rilegislature.gov/SiteAssets/MailingLists/Senators.xls"

    def postprocess_response(self) -> None:
        wb = xlrd.open_workbook(file_contents=self.response.content)
        self.worksheet = wb.sheet_by_index(0)

    def process_page(self):
        mapping = {}
        for rownum in range(1, self.worksheet.nrows):
            # for colnum in range(1, self.worksheet.ncols):
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
        print(images)
        image = images[2]
        print(image)
        image = image.get("src")
        print(image)

        self.input.image = image

        return self.input


class LegList(HtmlListPage):
    dependencies = {
        "sen_detail_mapping": SenExcelPage(),
        "assembly_detail_mapping": AssemblyExcelPage(),
    }

    def process_item(self, item):
        name = CSS("td").match(item)[1].text_content().strip().split(" ", 1)
        # Splitting name to take off Senator/Rep. from beginning
        name = name[1]
        district = CSS("td").match(item)[0].text_content()
        email = CSS("td").match(item)[2].text_content()

        # print(email)
        # something weird is happening with email above

        if self.chamber == "upper":
            _email, city_town, _name, party, office_addr = self.sen_detail_mapping[
                int(district)
            ]
        else:
            _email, city_town, _name, party, office_addr = self.assembly_detail_mapping[
                int(district)
            ]
        print(re.sub(",", "", _name.strip().split(" ", 1)[1]))
        print(name)
        print(re.sub(",", "", _name.strip().split(" ", 1)[1]) == name)

        print(re.sub(r"[A-Z]\.\s", "", _name.strip().split(" ", 1)[1]))

        if re.sub(
            r"[A-Z]\.\s", "", re.sub(",", "", _name.strip().split(" ", 1)[1])
        ) == re.sub(r"[A-Z]\.\s", "", re.sub(",", "", name)):
            excel_party = party
            excel_city_town = city_town
            excel_office_addr = office_addr
            if excel_party == "Democrat":
                excel_party = "Democratic"

        p = ScrapePerson(
            name=name,
            state="ri",
            party=excel_party,
            district=district,
            chamber=self.chamber,
        )

        if re.sub(
            r"[A-Z]\.\s", "", re.sub(",", "", _name.strip().split(" ", 1)[1])
        ) == re.sub(r"[A-Z]\.\s", "", re.sub(",", "", name)):
            p.extras["City/Town Represented"] = excel_city_town
            p.district_office.address = excel_office_addr

        bio = CSS("td center a").match_one(item).get("href")

        # Image(bio)

        # image = self.image(bio)
        # p.image = image

        p.email = email
        p.add_link(bio)
        p.add_source(self.source.url, note="Contact Web Page")
        # p.add_source(self.url, note="Detail Excel Source")

        return p
        return Image(p, source=bio)


class AssemblyList(LegList):
    source = "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=75)
    chamber = "lower"
    # url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Representatives.xls"


class SenList(LegList):
    source = "http://webserver.rilegislature.gov/Email/SenEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=38)
    chamber = "upper"
    # url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Senators.xls"
