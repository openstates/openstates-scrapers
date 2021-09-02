# import attr
# import re
from spatula import HtmlListPage, HtmlPage, CSS, SelectorError, XPath
from openstates.models import ScrapePerson


class SenDetail(HtmlPage):
    example_source = "https://malegislature.gov/Legislators/Profile/MJB0"

    def process_page(self):
        p = self.input

        try:
            position = CSS("#thumbCaption").match_one(self.root).text_content().strip()
            p.extras["position"] = position
        except SelectorError:
            pass

        # will always be capitol office, then district office listed
        address = CSS(".contactGroup a").match(self.root)

        capital_contact_info = CSS(".contactInfo .col-lg-3").match(self.root)
        print("CAPITALCONTACT INFO")
        for contact in capital_contact_info:
            print("capital text", contact.text_content().strip())
            if contact.text_content().strip() == "Fax:":
                fax_number = (
                    XPath(".//following-sibling::div")
                    .match_one(contact)
                    .text_content()
                    .strip()
                )
                p.capitol_office.fax = fax_number

        p.capitol_office.address = address[0].text_content().replace("  ", "")

        # try:
        #     p.district_office.address = address[1].text_content().replace("  ", "")
        # except IndexError:
        #     pass

        # try:
        #     district_contact_info = CSS(".contactInfo .col-lg-3").match(self.root)[1]
        #     for contact in district_contact_info:
        #         if contact.text_content().strip() == "Phone:":
        #             phone_number = (
        #                 XPath(".//following-sibling::div")
        #                 .match_one(contact)
        #                 .text_content()
        #                 .strip()
        #             )
        #             p.district_office.voice = phone_number
        #         elif contact.text_content().strip() == "Fax:":
        #             fax_number = (
        #                 XPath(".//following-sibling::div")
        #                 .match_one(contact)
        #                 .text_content()
        #                 .strip()
        #             )
        #             p.district_office.fax = fax_number
        # except IndexError:
        #     pass

        return p


class LegList(HtmlListPage):
    selector = CSS("#legislatorTable tbody tr")

    def process_item(self, item):
        __, image, first_name, last_name, district, party, room, phone, email = CSS(
            "td"
        ).match(item)
        url = CSS("a").match_one(first_name).get("href")

        image = CSS("img").match_one(image).get("src")

        p = ScrapePerson(
            name=first_name.text_content() + " " + last_name.text_content(),
            state="ma",
            party=party.text_content(),
            district=district.text_content(),
            chamber=self.chamber,
            image=image,
            email=email.text_content(),
        )

        p.capitol_office.voice = phone.text_content()
        p.add_source(self.source.url)
        p.add_source(url)

        return SenDetail(p, source=url)


class SenList(LegList):
    source = "https://malegislature.gov/Legislators/Members/Senate"
    chamber = "upper"


class RepList(LegList):
    source = "https://malegislature.gov/Legislators/Members/House"
    chamber = "lower"
