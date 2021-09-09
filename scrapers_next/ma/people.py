# import attr
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

        # will always be capitol office, then district office listed
        # https://malegislature.gov/Legislators/Profile/BMA1
        # https://malegislature.gov/Legislators/Profile/J_B1
        # https://malegislature.gov/Legislators/Profile/NAG1

        # https://malegislature.gov/Legislators/Profile/DRC1

        # offices = XPath("//div[@class='col-xs-12 col-sm-5']/h4")
        offices = CSS(".contactGroup").match(self.root)

        for office in offices:
            # for state, then district office
            fax_number = ""
            phone_number = ""
            address = ""
            office_title = (
                XPath("..//preceding-sibling::h4/text()").match_one(office).strip()
            )
            print("OFFICE TITLE", office_title)
            try:
                address = CSS("a").match_one(office).text_content().replace("  ", "")
                address = re.split(" \r\n|\r\n", address)
                # .split("\r\n")
                try:
                    address = f"{address[0]}, {address[1]}; {address[2]}"
                # print("address of this office", address)
                except IndexError:
                    address = f"{address[0]}; {address[1]}"
            except SelectorError:
                pass

            try:
                office_contact_info = CSS(".contactInfo .col-lg-3").match(office)
                # # print("phone and or fax", office_contact_info)
                # for ee in office_contact_info:
                #     print("type of contact info", ee.text_content())

                # print("OKAY NOW INVESTIGATE THIS")
                for contact in office_contact_info:
                    # print("capital text", contact.text_content().strip())
                    # print("START OF A NEW ")
                    # fax_number = ""
                    # phone_number = ""
                    if contact.text_content().strip() == "Fax:":
                        # print("fax number is here")
                        fax_number = (
                            XPath(".//following-sibling::div[1]")
                            .match_one(contact)
                            .text_content()
                            .strip()
                        )
                        print("this is the fax number", fax_number)
                    if contact.text_content().strip() == "Phone:":
                        # p.capitol_office.fax = fax_number
                        # print("thisistrgigga")
                        # print(XPath(".//following-sibling::div[1]").match_one(contact).text_content())
                        # .match_one(contact)
                        # .text_content())
                        # print("this is the phone number")
                        phone_number = (
                            XPath(".//following-sibling::div[1]")
                            .match_one(contact)
                            .text_content()
                            .strip()
                        )
                        print("HELLOOOO PHONE", phone_number)

            except SelectorError:
                pass
            if office_title == "State House":
                # print("the above is for state")
                # try:\
                if address:
                    p.capitol_office.address = address
                if fax_number:
                    print("test", fax_number)
                    p.capitol_office.fax = fax_number
                print("the above is for state")
                # if phone_number:
                # except ValueError:

                # p.capitol_office.fax = fax_number
                # print("capitol fax", fax_number)
            elif office_title == "District Office":
                # print("the above is for district")
                # print("distri")
                if address:
                    p.district_office.address = address
                if fax_number:
                    print("test", fax_number)
                    p.district_office.fax = fax_number
                if phone_number:
                    print("test", phone_number)
                    p.district_office.voice = phone_number
                print("the above is for district")
                # print("distrct phone", phone_number)
                # print("district fax", fax_number)

        # address = CSS(".contactGroup a").match(self.root)

        # capitol_contact_info = CSS(".contactInfo .col-lg-3").match(self.root)
        # print("CAPITALCONTACT INFO")

        # # capital_contact
        # # make into separate function
        # # contact_info(capitol_contact_info)
        # for contact in capitol_contact_info:
        #     print("capital text", contact.text_content().strip())
        #     if contact.text_content().strip() == "Fax:":
        #         fax_number = (
        #             XPath(".//following-sibling::div")
        #             .match_one(contact)
        #             .text_content()
        #             .strip()
        #         )
        #         p.capitol_office.fax = fax_number

        # p.capitol_office.address = address[0].text_content().replace("  ", "")

        # try:
        #     district_office_address = CSS("a").match_one(address[1]).text_content()
        #     print("DISTIRCT OFFICE", district_office_address)

        # except IndexError:
        #     pass

        # try:

        # except SelectorError:

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
