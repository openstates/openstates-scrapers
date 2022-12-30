import re
from spatula import HtmlListPage, CSS, XPath
from openstates.models import ScrapePerson


class AssemblyList(HtmlListPage):
    source = "https://www.assembly.ca.gov/assemblymembers"
    selector = CSS("table tbody tr", num_items=80)

    cap_off_suite_regex = re.compile(r"Capitol Office, (.+)(Suite \d{4})")
    cap_off_room_regex = re.compile(r"Capitol Office, (.+)(Room \d{3})")
    po_box_regex = re.compile(r"(P\.O\. Box.+;)\s+(\(\d{3}\)\s+\d{3}-\d{4})")
    dist_addr_only_regex = re.compile(r"(.+,\s+CA\s+\d{5}-*\d*)")
    dist_phone_only_regex = re.compile(r"(\(\d{3}\)\s+\d{3}-\d{4})")

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
            image=photo_url or "",
        )

        headers = CSS("h3").match(item)
        cap_off_addr_part = "1021 O Street"

        for header in headers:
            h3_text = header.text_content()

            suite_match = self.cap_off_suite_regex.search(h3_text)
            if suite_match:
                cap_off_addr_part = "".join(suite_match.groups())

            room_match = self.cap_off_room_regex.search(h3_text)
            if room_match:
                cap_off_addr_part = "".join(room_match.groups())

            p.capitol_office.address = f"{cap_off_addr_part}" ", Sacramento, CA 95814"

            po_box_and_phone = XPath("./td[4]/text()").match(item)[1].strip()
            po_box, cap_phone = self.po_box_regex.search(po_box_and_phone).groups()

            p.capitol_office.voice = cap_phone
            p.extras["P.O. Box"] = po_box

            if "District Office" in h3_text:
                dist_offs = header.getnext().text_content().strip()
                dist_list = []
                if len(dist_offs):
                    dist_list = [x for x in dist_offs.split(" edit") if len(x)]
                dist_addr_match = self.dist_addr_only_regex.search(dist_list[0])
                if dist_addr_match:
                    (p.district_office.address,) = dist_addr_match.groups()
                dist_phone_match = self.dist_phone_only_regex.search(dist_list[0])
                if dist_phone_match:
                    (p.district_office.voice,) = dist_phone_match.groups()
                # Remove primary office before processing additional offices
                dist_list.pop(0)
                for off in dist_list:
                    addr_match = self.dist_addr_only_regex.search(off)
                    phone_match = self.dist_phone_only_regex.search(off)
                    extra_off_addr, extra_off_phone = "", ""
                    if addr_match:
                        (extra_off_addr,) = addr_match.groups()
                    if phone_match:
                        (extra_off_phone,) = phone_match.groups()

                    p.add_office(
                        classification="district",
                        address=extra_off_addr,
                        voice=extra_off_phone,
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
