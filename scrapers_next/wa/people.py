from spatula import HtmlListPage, CSS
from ..common.people import ScrapePerson

# , ScrapeContactDetail


class SenList(HtmlListPage):
    source = "https://app.leg.wa.gov/ContentParts/MemberDirectory/?a=Senate"
    selector = CSS("#allMembers .memberInformation", num_items=49)

    PARTY_MAP = {"(R)": "Republican", "(D)": "Democratic"}

    def process_item(self, item):
        name = CSS(".memberName").match_one(item).text_content()[8:-4]
        # print(name)
        party = self.PARTY_MAP[CSS(".memberName").match_one(item).text_content()[-3:]]
        # print(party)
        district = (
            CSS(".visible-csm.visible-sm.visible-md").match(item)[1].text_content()
        )
        # [1].text
        # print(district)
        # leg_url = (
        #    CSS(".visible-csm.visible-sm.visible-md").match(item)[0].get("href")
        # )
        # print(leg_url)
        image = CSS(".memberImage").match_one(item).get("src")

        capitol_office_addr = (
            CSS(".memberColumnTitle + span").match(item)[0].text_content()
        )
        # capitol_office_addr = CSS(".memberColumnTitle + span span").match(item)[0].text_content()
        # capitol_office_addr += CSS(".memberColumnTitle + span br").match(item)[0].nextSibling
        # capitol_office_addr += CSS(".memberColumnTitle + span br").match(item)[1].nextSibling
        # TODO
        # get capitol office voice (phone)

        phone = (
            CSS("div .col-csm-6.col-md-3.memberColumnPad > div")
            .match(item)[1]
            .text_content()[-14:]
        )
        print(phone)

        p = ScrapePerson(
            name=name,
            state="wa",
            chamber="upper",
            district=district,
            party=party,
            image=image,
        )
        p.capitol_office.address = capitol_office_addr
        p.capitol_office.voice = phone
        return p


# should district be 17 or 17th Legislative District?

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
