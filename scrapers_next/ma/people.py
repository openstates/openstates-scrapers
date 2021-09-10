import re
from spatula import HtmlListPage, HtmlPage, CSS, SelectorError, XPath
from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    # example_source = "https://malegislature.gov/Legislators/Profile/MJB0"
    # example_source = "https://malegislature.gov/Legislators/Profile/NAG1"
    example_source = "https://malegislature.gov/Legislators/Profile/BMA1"

    def process_page(self):
        p = self.input

        try:
            position = CSS("#thumbCaption").match_one(self.root).text_content().strip()
            p.extras["position"] = position
        except SelectorError:
            pass

        offices = CSS(".contactGroup").match(self.root)

        # state and/or district offices can have different kinds of information
        for office in offices:

            fax_number = ""
            phone_number = ""
            address = ""
            office_title = (
                XPath("..//preceding-sibling::h4/text()").match_one(office).strip()
            )

            try:
                address = CSS("a").match_one(office).text_content().replace("  ", "")
                address = re.split(" \r\n|\r\n", address)
                try:
                    address = f"{address[0]}, {address[1]}; {address[2]}"
                except IndexError:
                    address = f"{address[0]}; {address[1]}"
            except SelectorError:
                pass

            try:
                office_contact_info = CSS(".contactInfo .col-lg-3").match(office)

                for contact in office_contact_info:

                    if contact.text_content().strip() == "Fax:":
                        fax_number = (
                            XPath(".//following-sibling::div[1]")
                            .match_one(contact)
                            .text_content()
                            .strip()
                        )

                    if contact.text_content().strip() == "Phone:":
                        phone_number = (
                            XPath(".//following-sibling::div[1]")
                            .match_one(contact)
                            .text_content()
                            .strip()
                        )

            except SelectorError:
                pass
            if office_title == "State House":
                if address:
                    p.capitol_office.address = address
                if fax_number:
                    p.capitol_office.fax = fax_number

            elif office_title == "District Office":

                if address:
                    p.district_office.address = address
                if fax_number:
                    p.district_office.fax = fax_number
                if phone_number:
                    p.district_office.voice = phone_number

        links = XPath("//ul[@role='tablist']/li/a").match(self.root)
        for link in links:
            p.add_link(link.get("href"))

        return p


class LegList(HtmlListPage):
    selector = CSS("#legislatorTable tbody tr")

    def process_item(self, item):
        __, image, first_name, last_name, district, party, room, phone, email = CSS(
            "td"
        ).match(item)
        url = CSS("a").match_one(first_name).get("href")

        image = CSS("img").match_one(image).get("src")

        party = party.text_content()
        if party == "Unenrolled":
            party = "Independent"

        p = ScrapePerson(
            name=first_name.text_content() + " " + last_name.text_content(),
            state="ma",
            party=party,
            district=district.text_content(),
            chamber=self.chamber,
            image=image,
            email=email.text_content(),
        )

        p.capitol_office.voice = phone.text_content()
        p.add_source(self.source.url)
        p.add_source(url)

        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://malegislature.gov/Legislators/Members/Senate"
    chamber = "upper"


class RepList(LegList):
    source = "https://malegislature.gov/Legislators/Members/House"
    chamber = "lower"
