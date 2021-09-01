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
            # print("POSITION", position.text_content().strip())
            p.extras["position"] = position
            print("POSITION", position)
        except SelectorError:
            pass

        # address
        # TODO: is this address okay? with the spacing and everything (run a full scrape first)
        address = CSS(".contactGroup a").match_one(self.root)
        print("ADDRESS", address.text_content().replace("  ", ""))
        # for add in address:
        #     print("ADDY", add.text_content())
        # print("Address", address.text_content().strip())

        # fax number if there is one
        # contacts
        # contacts = CSS("")
        contact_info = CSS(".contactInfo .col-lg-3").match(self.root)
        # will get ["Phone:", "Fax:"]
        for contact in contact_info:
            # print("cycling through")
            # print("contact text", contact.text_content().strip())
            if contact.text_content().strip() == "Fax:":
                # print("HELLO THERE")
                # then go to next sibling:
                # td/following-sibling::td[1]
                fax_number = (
                    XPath(".//following-sibling::div")
                    .match_one(contact)
                    .text_content()
                    .strip()
                )
                p.capitol_office.fax = fax_number

        # add fax number and phone number to this address
        p.capitol_office.address = address.text_content().replace("  ", "")
        # p.district_office.voice = self.input.phone
        # p.district_office.fax = fax_number

        # p.add_source(self.input.source)

        return p


class SenList(HtmlListPage):
    source = "https://malegislature.gov/Legislators/Members/Senate"
    selector = CSS("#legislatorTable tbody tr")

    # TODO: one person (Michael Barrett) has a fax number that's listed on indiv page and not main page...

    # on indiv page: also there's position (can be added to extras), and possible fax number, more specific address as well
    def process_item(self, item):
        # print(item.text_content())
        __, image, first_name, last_name, district, party, room, phone, email = CSS(
            "td"
        ).match(item)
        print("name", first_name.text_content(), last_name.text_content())
        url = CSS("a").match_one(first_name).get("href")
        print("URL", url)
        # name = first_name.text_content() + " " + last_name.text_content()
        # print("NAME", name)

        image = CSS("img").match_one(image).get("src")

        p = ScrapePerson(
            name=first_name.text_content() + " " + last_name.text_content(),
            state="ma",
            party=party.text_content(),
            district=district.text_content(),
            chamber="upper",
            image=image,
            email=email.text_content(),
        )

        p.capitol_office.voice = phone.text_content()
        p.add_source(self.source.url)
        p.add_source(url)

        # return p
        return SenDetail(p, source=url)

        # name = item[2].text.replace("  ", " ")
        # url = item[0].get("href")
        # district = re.match(r"District (\d+)", item[4].text)[1]
        # image = item[0][0].get("src")
        # return SenatorDetail(PartialMember(name, url, district, image), source=url)
