import re
from spatula import HtmlListPage, CSS, XPath, URL
from ..common.people import ScrapePerson


class PartyAugmentation(HtmlListPage):
    """
    WA Email addresses are listed on a separate page.
    """

    source = URL("https://app.leg.wa.gov/memberemail/Default.aspx")

    def find_rows(self):
        for table in CSS("#membertable").match(self.root):
            rows = CSS("tbody tr").match(table)
            if len(rows) == 147:
                return rows

    def process_page(self):
        # We need it to find the member's email address.
        # These positions are enough to discriminate the chamber too (0 = upper, 1,2 = lower)
        mapping = {}
        rows = self.find_rows()
        for row in rows:
            tds = row.getchildren()
            name = (
                CSS("a")
                .match_one(tds[0])
                .text_content()
                .lstrip(r"^(Rep\.|Senator)")
                .strip()
            )
            email = tds[1].text_content().strip()
            dist = tds[2].text_content().strip()
            position = tds[3].text_content().strip()
            party = tds[4].text_content().strip()
            mapping[name] = (email, party, dist, position)
        return mapping


class LegList(HtmlListPage):
    dependencies = {"party_mapping": PartyAugmentation()}

    def process_item(self, item):
        title_name_party = XPath('.//span[@class="memberName"]/text()').match_one(item)

        (name, party) = re.search(
            r"^(?:Senator|Representative)\s(.+)\s\(([RD])\)$", title_name_party
        ).groups()
        if party == "R":
            party = "Republican"
        elif party == "D":
            party = "Democratic"

        (district_name, _district_name) = XPath(
            ".//a[contains(text()," ' " Legislative District")]/text()'
        ).match(item)

        assert (
            district_name.strip("Legislative District").strip()
            == _district_name.strip("Legislative District").strip()
        )
        district_num = re.search(
            r"(\d{1,2})\w{2} Legislative District", district_name
        ).group(1)

        image = XPath('.//a[text()="Print Quality Photo"]/@href').match_one(item)

        capitol_office = (
            CSS("div.col-csm-6.col-md-3.memberColumnPad > div")
            .match(item)[1]
            .text_content()
            .splitlines()
        )
        capitol_office = [line.strip() for line in capitol_office if line.strip()]
        capitol_phone = None
        capitol_address = []

        for line in capitol_office:
            if re.search(r"^\(\d{3}\)", line):
                capitol_phone = line
            elif line == "Olympia Office":
                continue
            else:
                capitol_address.append(line)

        capitol_address = "; ".join(capitol_address)

        _has_district_office = XPath(
            './/div[@class="memberColumnTitle" and text()="District Office"]'
        ).match(item, min_items=0)

        if len(_has_district_office) > 0:
            district_office = (
                XPath(
                    './/div[@class="memberColumnTitle" and'
                    ' text()="District Office"]/..'
                )
                .match_one(item)
                .text_content()
                .splitlines()
            )
            district_office = [line.strip() for line in district_office if line.strip()]
            district_phone = None
            district_address = []

            for line in district_office:
                if re.search(r"^\(\d{3}\)", line):
                    district_phone = line
                elif line == "District Office":
                    continue
                else:
                    district_address.append(re.sub(r"[\s\s]+", " ", line))

            district_address = "; ".join(district_address)

        p = ScrapePerson(
            name=name,
            state="wa",
            chamber=self.chamber,
            district=district_num,
            party=party,
            image=image,
        )
        p.capitol_office.address = capitol_address
        p.capitol_office.voice = capitol_phone

        if len(_has_district_office) > 0:
            p.district_office.address = district_address
            if district_phone:
                p.district_office.voice = district_phone

        p.add_link(XPath('.//a[contains(text(), "Home Page")]/@href').match(item)[0])
        p.add_source(str(self.source))
        p.add_source(str(PartyAugmentation.source))

        spans = CSS("div .col-csm-8 span").match(item)
        if len(spans) == 3:
            p.extras["title"] = spans[1].text_content()

        (dep_email, dep_party, dep_dist, dep_pos) = self.party_mapping[name]
        if dep_party == "R":
            dep_party = "Republican"
        elif dep_party == "D":
            dep_party = "Democratic"

        if (
            (self.chamber == "upper" and dep_pos == "0")
            or (self.chamber == "lower" and dep_pos != "0")
            and dep_party == party
            and dep_dist == district_num
        ):
            p.email = dep_email

        return p


class RepList(LegList):
    source = "https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=House"
    selector = CSS("#allMembers .memberInformation", num_items=98)
    chamber = "lower"


class SenList(LegList):
    source = "https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=Senate"
    selector = CSS("#allMembers .memberInformation", num_items=49)
    chamber = "upper"
