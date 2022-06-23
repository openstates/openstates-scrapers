import re
from spatula import HtmlListPage, CSS, XPath, URL
from openstates.models import ScrapePerson


class LegList(HtmlListPage):
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
            './/a[contains(text(), "Legislative District")]/text()'
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
        p.add_source(self.source.url)

        spans = CSS("div .col-csm-8 span").match(item)
        if len(spans) == 3:
            p.extras["title"] = spans[1].text_content()

        return p


class RepList(LegList):
    source = URL("https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=House", timeout=30)
    selector = CSS("#allMembers .memberInformation", num_items=98)
    chamber = "lower"


class SenList(LegList):
    source = URL("https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=Senate", timeout=30)
    selector = CSS("#allMembers .memberInformation", min_items=45, max_items=49)
    chamber = "upper"
