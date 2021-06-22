import re
from spatula import HtmlListPage, CSS, XPath
from ..common.people import ScrapePerson


class SenList(HtmlListPage):
    source = "https://www.senate.ca.gov/senators"
    selector = CSS("div .view-content > div", num_items=40)

    def process_item(self, item):
        name = XPath(".//h3/text()").match(item)[0]
        if name.endswith(" (R)"):
            party = "Republican"
        elif name.endswith(" (D)"):
            party = "Democratic"
        else:
            self.warning("skipping " + name)
            return None
        name = name.split(" (")[0]

        district = (
            XPath('.//div[contains(@class, "senator-district")]/div/text()')
            .match(item)[0]
            .strip()
            .lstrip("0")
        )

        photo_url = XPath(".//img/@src").match_one(item)

        p = ScrapePerson(
            name=name,
            state="ca",
            chamber="upper",
            district=district,
            party=party,
            image=photo_url,
        )

        capitol_office = XPath(
            ".//div[contains(@class, 'views-field-field-senator-capitol-office')]//p"
        ).match_one(item)
        capitol_address, capitol_phone = capitol_office.text_content().split("; ")
        p.capitol_office.address = capitol_address.strip()
        p.capitol_office.voice = capitol_phone.strip()

        # n = 1
        district_office = XPath(
            ".//div[contains(@class, 'views-field-field-senator-district-office')]"
        ).match_one(item)
        for addr in district_office.text_content().strip().splitlines():
            try:
                if re.search(r"District Offices?", addr):
                    continue
                # note = "District Office #{}".format(n)
                # print(addr)
                addr, phone = addr.strip().split("; ")
                # print(addr)
                # print(phone)
                p.district_office.address = addr.strip()
                p.district_office.voice = phone.strip()
                # p.district_office.note = note
                # p.district_office.address = addr
                # n += 1
            except ValueError:
                # Steven Bradford separated by period ...
                continue

        url = XPath(".//a/@href").match(item)[0]
        p.add_link(url)
        p.add_source(self.source.url)

        return p
