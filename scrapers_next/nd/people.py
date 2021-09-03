from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath  # , SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("div.field-person-photo img").match_one(self.root).get("src")
        # print(img)
        p.image = img

        # bio_info = CSS("div.pane-content ul li").match(self.root)
        # occupation = bio_info[0].text_content().strip()
        # education = bio_info[1].text_content().strip()
        # military = bio_info[2].text_content().strip()
        # other_pos = bio_info[3].text_content().strip()
        # service = bio_info[4].text_content().strip()
        # print(len(bio_info))

        # try:
        #     street = (
        #         CSS("div.street-address").match_one(self.root).text_content().strip()
        #     )
        #     town = CSS("span.locality").match_one(self.root).text_content().strip()
        #     zip_code = (
        #         CSS("span.postal-code").match_one(self.root).text_content().strip()
        #     )
        #     address = street + ", " + town + ", ND " + zip_code
        #     # print(address)
        # except SelectorError:
        #     pass

        # Cellphone:
        # Home Telephone:
        # Office Telephone:
        # try:
        #     phones_lower = XPath("//*[@id='block-system-main']//div[contains(text(), 'phone')]").match(self.root)
        #     for phone in phones_lower:
        #         phone_type = phone.text_content().strip()
        #         print(phone_type)
        #         phone_number = phone.getnext().text_content().strip()
        #         print(phone_number)
        # except SelectorError:
        #     pass

        # try:
        #     phones_upper = XPath("//*[@id='block-system-main']//div[contains(text(), 'Phone')]").match(self.root)
        #     for phone in phones_upper:
        #         phone_type = phone.text_content().strip()
        #         print(phone_type)
        #         phone_number = phone.getnext().text_content().strip()
        #         print(phone_number)
        # except SelectorError:
        #     pass

        # email
        email = (
            XPath("//*[@id='block-system-main']//div[contains(text(), 'Email')]")
            .match_one(self.root)
            .getnext()
            .text_content()
            .strip()
        )
        # print(email)
        p.email = email

        return p


class LegList(HtmlListPage):
    source = URL(
        "https://www.legis.nd.gov/assembly/67-2021/members/members-by-district"
    )
    selector = CSS("div.view-content > div", num_items=142)

    def process_item(self, item):
        name = CSS("div.name").match_one(item).text_content().strip()
        name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]

        chamber = CSS("div.chamber").match_one(item).text_content().strip()
        if chamber == "Senate":
            chamber = "upper"
        elif chamber == "House":
            chamber = "lower"

        for previous_tag in item.itersiblings(preceding=True):
            if previous_tag.get("class") == "title":
                district = previous_tag.text_content().strip()
                district = re.search(r"District\s(.+)", district).groups()[0]
                break

        party = CSS("div.party").match_one(item).text_content().strip()
        if party == "Democrat":
            party = "Democratic"

        p = ScrapePerson(
            name=name,
            state="nd",
            chamber=chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("div.name a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegDetail(p, source=detail_link)
