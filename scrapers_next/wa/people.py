import re
from spatula import HtmlListPage, CSS, XPath, URL
from ..common.people import ScrapePerson

# , ScrapeContactDetail


class PartyAugmentation(HtmlListPage):
    """
    WA Email addresses are listed on a separate page.
    """

    source = URL("https://app.leg.wa.gov/memberemail/Default.aspx")

    def find_rows(self):
        # print(CSS("html body").match(self.root)[0].getchildren()[0].text_content())
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
            mapping[(dist, position)] = (name, email, party)
            # print(mapping)
        return mapping


# leg list if works for reps as well
# just need to change source and selector
# sen list and rep list with different sources

# class LegList
# class SenList(LegList):
# class RepList(LegList):


class SenList(HtmlListPage):
    source = "https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=Senate"
    selector = CSS("#allMembers .memberInformation", num_items=49)
    dependencies = {"party_mapping": PartyAugmentation()}

    def process_item(self, item):
        # name = CSS(".memberName").match_one(item).text_content()[8:-4]
        # print(name)
        # party = self.PARTY_MAP[CSS(".memberName").match_one(item).text_content()[-3:]]
        # print(party)

        # (title_name_party,) = member.xpath('.//span[@class="memberName"]/text()')
        # print(CSS(".memberName").match(item)[0].text_content())

        title_name_party = CSS(".memberName").match(item)[0].text_content()
        (name, party) = re.search(
            r"^(?:Senator|Representative)\s(.+)\s\(([RD])\)$", title_name_party
        ).groups()
        if party == "R":
            party = "Republican"
        elif party == "D":
            party = "Democratic"

        # district = (
        #    CSS(".visible-csm.visible-sm.visible-md").match(item)[1].text_content()
        # )

        (district_name, _district_name) = XPath(
            ".//a[contains(text()," ' " Legislative District")]/text()'
        ).match(item)
        # print(district_name.strip('Legislative District').strip(),
        # _district_name.strip('Legislative District').strip())
        assert (
            district_name.strip("Legislative District").strip()
            == _district_name.strip("Legislative District").strip()
        )
        district_num = re.search(
            r"(\d{1,2})\w{2} Legislative District", district_name
        ).group(1)

        # print(district)
        # leg_url = (
        #    CSS(".visible-csm.visible-sm.visible-md").match(item)[0].get("href")
        # )
        # print(leg_url)

        # image = CSS(".memberImage").match_one(item).get("src")
        image = ""
        # capitol_office = CSS(".memberColumnTitle + span").match(item)[0].text_content()
        # print(capitol_office)
        # print(CSS(".memberColumnTitle ~ br").nextSibling.match_one(item))

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
            if line.startswith("(360)"):
                capitol_phone = line
            elif line == "Olympia Office":
                continue
            else:
                capitol_address.append(line)

        capitol_address = "; ".join(capitol_address)

        # './/div[@class="memberColumnTitle" and'
        # 'text()=" Olympia Office"]/parent::div[1]/text()'
        # 'div.col-csm-6.col-md-3.memberColumnPad > div'
        # contains(text(), "Home Page")
        _has_district_office = XPath(
            './/div[@class="memberColumnTitle" and text()="District Office"]'
        ).match(item, min_items=0)
        # print(_has_district_office)

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
            # print(district_office)
            district_office = [line.strip() for line in district_office if line.strip()]
            # print(district_office)
            district_phone = None
            district_address = []

            for line in district_office:
                # print(line)
                if re.search(r"^\(\d{3}\)", line):
                    # line.str.contains(r"\(\d{3}\)"):
                    district_phone = line
                elif line == "District Office":
                    continue
                else:
                    district_address.append(re.sub(r"[\s\s]+", " ", line))

            district_address = "; ".join(district_address)
            # print(district_address)
        #    if capitol_office[-1].startswith("Fax: "):
        #        capitol_fax = capitol_office.pop().replace("Fax: ", "")

        p = ScrapePerson(
            name=name,
            state="wa",
            chamber="upper",
            district=district_num,
            party=party,
            image=image,
        )
        p.capitol_office.address = capitol_address
        p.capitol_office.voice = capitol_phone
        # print(district_address)
        # print(district_phone)
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

        # print(self.party_mapping)
        # print(district_num)
        # print(self.party_mapping[(district_num, '0')])
        (dep_name, dep_email, dep_party) = self.party_mapping[(district_num, "0")]
        if dep_party == "R":
            dep_party = "Republican"
        elif dep_party == "D":
            dep_party = "Democratic"
        # print(dep_name == name)
        # print(dep_party == party)

        if dep_name == name and dep_party == party:
            p.email = dep_email
            # print(p.email)

        return p


# TODO
# add representatives
# add image back in
