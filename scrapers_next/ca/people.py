import re
from spatula import HtmlListPage, CSS, XPath
from openstates.models import ScrapePerson


class AssemblyList(HtmlListPage):
    source = "https://www.assembly.ca.gov/assemblymembers"
    selector = CSS("table tbody tr", num_items=80)

    def process_item(self, item):
        name = CSS("a").match(item)[2].text_content()
        name = re.sub(r"Contact Assembly Member", "", name).strip()

        party = CSS("td").match(item)[2].text_content().strip()
        if party == "Democrat":
            party = "Democratic"

        district = CSS("td").match(item)[1].text_content().strip().lstrip("0")

        # District 18 has a vacant spot
        if name == "edit":
            self.skip("skipping Vacant seat in District {}".format(district))

        photo_url = CSS("img").match(item, min_items=0)
        if photo_url:
            photo_url = photo_url[0].get("src")

        p = ScrapePerson(
            name=name,
            state="ca",
            chamber="lower",
            district=district,
            party=party,
            image=photo_url,
        )

        capitol_office_header = CSS("h3").match(item)[0].text_content()
        capitol_office_text = (
            XPath(
                "//*[@id='block-views-view-members-block-1']/div/div/div/table/tbody/tr[1]/td[4]/text()"
            )
            .match(item)[1]
            .strip()
        )
        capitol_office_text, capitol_office_phone = capitol_office_text.split("; ")
        capitol_office_address = capitol_office_header + capitol_office_text

        p.capitol_office.address = capitol_office_address
        p.capitol_office.voice = capitol_office_phone

        district_offices = XPath(".//td/p[1]/text()").match(item)

        for office in district_offices:
            district_address, district_phone = office.split("; ")
            p.add_office(
                contact_type="District Office",
                address=district_address.strip(),
                voice=district_phone.strip(),
            )

        url = CSS("a").match(item)[0].get("href")
        p.add_link(url)
        p.add_source(self.source.url)

        return p


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
            self.skip("skipping " + name)
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
        capitol_address, capitol_phone = (
            capitol_office.text_content().replace(u"\xa0", " ").split("; ")
        )
        p.capitol_office.address = capitol_address.strip()
        p.capitol_office.voice = capitol_phone.strip()

        district_office = XPath(
            ".//div[contains(@class, 'views-field-field-senator-district-office')]"
        ).match_one(item)
        for line in district_office.text_content().strip().splitlines():
            try:
                if re.search(r"District Offices?", line):
                    continue
                addr, phone = line.strip().replace(u"\xa0", " ").split("; ")
                p.add_office(
                    contact_type="District Office",
                    address=addr.strip(),
                    voice=phone.strip(),
                )
            except ValueError:
                # Steven Bradford address/phone separated by period instead of semi-colon
                if re.search(r"\w+\.\s\(\d{3}\)", line):
                    addr, phone = line.strip().replace(u"\xa0", " ").split(". (")
                    phone = "(" + phone
                    p.add_office(
                        contact_type="District Office",
                        address=addr.strip(),
                        voice=phone.strip(),
                    )

        url = XPath(".//a/@href").match(item)[0]
        p.add_link(url)
        p.add_source(self.source.url)

        return p
