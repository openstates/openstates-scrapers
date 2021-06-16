import re
from spatula import HtmlListPage, CSS, XPath
from ..common.people import ScrapePerson

# , ScrapeContactDetail


class SenList(HtmlListPage):
    source = "https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=Senate"
    selector = CSS("#allMembers .memberInformation", num_items=49)

    # PARTY_MAP = {"(R)": "Republican", "(D)": "Democratic"}

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

        image = CSS(".memberImage").match_one(item).get("src")

        capitol_office = CSS(".memberColumnTitle + span").match(item)[0].text_content()
        # print(capitol_office)
        # print(CSS(".memberColumnTitle ~ br").nextSibling.match_one(item))

        print(
            CSS("div.col-csm-6.col-md-3.memberColumnPad > div")
            .match(item)[1]
            .text_content()
        )
        # capitol_office = CSS(".memberColumnTitle + span").match(item)[0].text_content()

        # capitol office address line 1
        # capitol_office = XPath(
        #    './/div[@class="memberColumnTitle" and'
        #    'text()="Olympia Office"]/parent::div[1]/span'
        # ).match_one(item).text_content()
        # print(capitol_office_addr1)
        # capitol office address lines 2 and 3
        # capitol_office_addr2 = XPath(
        #    './/div[@class="memberColumnTitle" and'
        #    'text()="Olympia Office"]/parent::div[1]/span/text()'
        # ).match(item)
        # print(capitol_office_addr2)
        # capitol office address line 4 (phone)
        # capitol_phone = XPath(
        #    './/div[@class="memberColumnTitle" and'
        #    'text()="Olympia Office"]/parent::div[1]'
        # ).match(item).text_content()
        # print(capitol_office_phone)

        # print(capitol_office)
        # capitol_office = [s.strip() for s in capitol_office if s.strip()]
        # print(capitol_office)
        # capitol_fax = None
        # capitol_phone = None
        # capitol_address = None
        # Can't capture any information anyway if office data is empty,
        # so we can skip if that's the case.
        # if capitol_office:
        # Retrieve capitol office fax number.
        #    if capitol_office[-1].startswith("Fax: "):
        #        capitol_fax = capitol_office.pop().replace("Fax: ", "")

        # Retrieve capitol office phone number.
        # capitol_phone = capitol_office.pop()

        # Retrieve capitol office address.
        # capitol_address = "\n".join(capitol_office)
        # print(capitol_fax)
        # print(capitol_phone)
        # print(capitol_address)
        # capitol_office_addr = (
        #    CSS(".memberColumnTitle + span").match(item)[0].text_content()
        # )
        # capitol_office_addr = CSS(".memberColumnTitle + span span").match(item)[0].text_content()
        # capitol_office_addr += CSS(".memberColumnTitle + span br").match(item)[0].nextSibling
        # capitol_office_addr += CSS(".memberColumnTitle + span br").match(item)[1].nextSibling
        # TODO
        # get capitol office voice (phone)

        # phone = (
        #    CSS("div .col-csm-6.col-md-3.memberColumnPad > div")
        #    .match(item)[1]
        #    .text_content()[-14:]
        # )
        # print(phone)

        # Email addresses are listed on a separate page.
        # email_list_url = "http://app.leg.wa.gov/memberemail/Default.aspx"

        # Retrieve the member's position from the email link.
        # We need it to find the member's email address.
        # These positions are enough to discriminate the chamber too (0 = upper, 1,2 = lower)
        email_link_url = (
            XPath('.//a[contains(@href, "memberEmail")]').match(item)[0].get("href")
        )
        print(email_link_url)
        position = re.search(r"/([[0-9]+)$", email_link_url).group(1)
        print(position)

        # Need to get the email from the email page by matching -
        # with the member's district and position
        # try:
        email = (
            XPath(
                './/tr/td/a[contains(@href, "memberEmail/{}/{}")]/parent::td/'
                "following-sibling::td[1]/text()"
            )
            .format(district_num, position)
            .strip()
        )
        # except AttributeError:
        #    email = ""
        print(email)
        p = ScrapePerson(
            name=name,
            state="wa",
            chamber="upper",
            district=district_num,
            party=party,
            image=image,
        )
        p.capitol_office.address = capitol_office
        p.capitol_office.voice = capitol_office
        p.add_link(XPath('.//a[contains(text(), "Home Page")]/@href').match(item)[0])

        return p


# TODO
# email: str = ""
# given_name: str = ""
# family_name: str = ""
# suffix: str = ""
# links: list[Link] = []
# sources: list[Link] = []
# ids: PersonIdBlock = PersonIdBlock()
# capitol_office = ScrapeContactDetail(note="Capitol Office")
# district_office = ScrapeContactDetail(note="District Office")
# extras: dict = {}
