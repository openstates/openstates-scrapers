# import attr
# import re
from spatula import HtmlListPage, CSS
from openstates.models import ScrapePerson


class SenList(HtmlListPage):
    source = "https://malegislature.gov/Legislators/Members/Senate"
    selector = CSS("#legislatorTable tbody tr")

    # TODO: one person (Michael Barrett) has a fax number that's listed on indiv page and not main page...
    def process_item(self, item):
        # print(item.text_content())
        __, image, first_name, last_name, district, party, room, phone, email = CSS(
            "td"
        ).match(item)
        print("name", first_name.text_content(), last_name.text_content())
        # name = first_name.text_content() + " " + last_name.text_content()
        # print("NAME", name)

        image = CSS("a").match_one(image).get("href")

        p = ScrapePerson(
            name=first_name.text_content() + " " + last_name.text_content(),
            state="ma",
            party=party.text_content(),
            district=district.text_content(),
            chamber="upper",
            image=image,
        )

        return p

        # name = item[2].text.replace("  ", " ")
        # url = item[0].get("href")
        # district = re.match(r"District (\d+)", item[4].text)[1]
        # image = item[0][0].get("src")
        # return SenatorDetail(PartialMember(name, url, district, image), source=url)
