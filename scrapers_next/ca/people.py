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

        # vacant districts show up with an interesting name
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
                "./td[4]/text()"
            )
            .match(item)[1]
            .strip()
        )
        capitol_office_full_address, capitol_office_phone = capitol_office_text.split("; ")
        capitol_office_pobox, office_city = capitol_office_full_address.split(",", 1)
        capitol_office_address = f"{capitol_office_header.removeprefix('Capitol Office, ')} {office_city.strip()}"

        p.capitol_office.address = capitol_office_address
        p.capitol_office.voice = capitol_office_phone
        p.extras["P.O. Box"] = f"{capitol_office_pobox} {office_city}"

        district_offices = XPath(".//td/p[1]/text()").match(item)
        district_phones = list()
        office = district_offices[0]
        district_address, district_phone = office.split("; ")
        p.district_office.address = district_address.strip()
        p.district_office.voice = district_phone.strip()
        district_phones.append(district_phone.strip())

        if len(district_offices) > 1:
            for office in district_offices[1:]:
                district_address, district_phone = office.split("; ")
                dist_phone = district_phone.strip()
                if dist_phone not in district_phones:
                    district_phones.append(dist_phone)
                    p.add_office(
                        classification="district",
                        address=district_address.strip(),
                        voice=dist_phone,
                    )
                else:
                    p.add_office(
                        classification="district",
                        address=district_address.strip(),
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
            capitol_office.text_content().replace("\xa0", " ").split("; ")
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
                addr, phone = line.strip().replace("\xa0", " ").split("; ")
                p.add_office(
                    classification="district",
                    address=addr.strip(),
                    voice=phone.strip(),
                )
            except ValueError:
                # Steven Bradford address/phone separated by period instead of semi-colon
                if re.search(r"\w+\.\s\(\d{3}\)", line):
                    addr, phone = line.strip().replace("\xa0", " ").split(". (")
                    phone = "(" + phone
                    p.add_office(
                        classification="district",
                        address=addr.strip(),
                        voice=phone.strip(),
                    )

        url = XPath(".//a/@href").match(item)[0]
        p.add_link(url)
        p.add_source(self.source.url)

        return p
