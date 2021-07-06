import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.people.models.committees import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)

        for link in XPath(
            '//div[contains(@class, "media-body")]//a[contains(@href, "member_bio")]'
        ).match(self.root):
            name = link.text_content().split(",")[0]
            if name:
                try:
                    positions = ("chair", "vice chair", "ranking minority member")
                    position = XPath("..//preceding-sibling::b/text()").match(link)
                    for role in position:
                        position_str = ""
                        position_str += role.lower()
                        if position_str not in positions:
                            raise ValueError("unknown position")
                except SelectorError:
                    position_str = "member"
            com.add_member(name, position_str)

        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://www.house.leg.state.mn.us/Committees/members/92002"

    def process_page(self):
        # print(XPath('//div[contains(@class, media-body)]//span//b').match(self.root).len())
        # print("name", XPath('//div[@class="media-body"]/span[1]/b/text()').match(self.root))
        for name in XPath(
            '//div[@class="media pl-2 py-4"]//div[@class="media-body"]'
        ).match(self.root):
            # if name != "Email: ":
            #     print("name", name)
            #     name_str = name
            # THIS WORKS:
            # name = XPath('//div[@class="media-body"]/span[1]/b/text()').match(self.root)
            # role = XPath("..//preceding-sibling").match(name)

            # name2 = XPath('./span[1]/b/text()').match(name)
            # if xpath doesn't work, then this does...nah doesn't work that well...
            # literalname2 = CSS("span b").match(name)[1].text_content()

            literalname2 = XPath(".//span/b/text()").match(name)[0]
            # if literalname2 in
            # lxml.etree.XPathEvalError: Unfinished literal
            # print("literal name", literalname2)
            # print("role!!", role)
            # print("person")

            # todo: should these be capitalized?
            positions = ["committee chair", "vice chair", "republican lead"]
            if name:
                try:
                    # note: maybe have to make role XPath relational so we don't get a long list :(--we want just one role
                    # role = XPath('//div[@class="media-body"]/span/b/u/text()').match(name)

                    # role = XPath("..//preceding-sibling::span/b/u/text()").match(name)
                    # position = XPath("..//preceding-sibling::b/text()").match(link)
                    position = CSS("span b u").match(name)[0].text_content().lower()
                    if position in positions:
                        role = position
                    # print("role", role)
                except SelectorError:
                    role = "member"
            print(literalname2, role)
            # com.add_member(name_str, role)

            # another idea: try, except--and then keep using following-sibling (or whatever) to find relevant info
            # on second thought, dont think thatll work
            # or, for each person blurb!
            # if the name includes Email: or "Administrator:" or "Legislative Assistant:" or "Fiscal Analyst:" then skip that
        # another thing: change this XPath below to be a little closer
        # for email in XPath('//div[contains(@class, media-body)]//span//a').match(self.root):
        # print(name)
        # name_str = email.text_content()
        # preceding-sibling: or/and preceding-sibling:
        # real_name =
        # name = XPath('.//preceding-sibling::b/text()').match(email)

        # position = XPath("..//preceding-sibling::b/text()").match(link)

        # print(name)

        # another idea:
        # for loop:
        # the only span>b is the position (if it exists)
        #


# from NC: HouseCommitteeList(CommitteeList)
# todo: add meeting times for each committee
class SenateCommitteeList(HtmlListPage):
    selector = CSS(" .card .list-group-flush .d-flex a")
    source = "https://www.senate.mn/committees"
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()
        # print(re.search('-', name))
        if re.search(" - ", name):
            parent, com_name = name.split(" - Subcommittee on ")
            # print("name is this: ", name)
            com = ScrapeCommittee(
                name=com_name, classification="subcommittee", parent=parent
            )
        else:
            com = ScrapeCommittee(name=name, parent=self.chamber)

        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=item.get("href"))


# todo: add meeting times, office building(?)
class HouseCommitteeList(HtmlListPage):
    # selector = CSS(".mb-3 .card-body h2 a")
    selector = CSS(".mb-3 .card-body")
    source = "https://www.house.leg.state.mn.us/committees"
    chamber = "lower"

    def process_item(self, item):
        link = (
            XPath(
                ".//div[contains(@class, 'container')]//a[contains(@href, 'members')]"
            )
            .match(item)[0]
            .get("href")
        )
        name = CSS("h2 a").match(item)[0].text_content()
        com = ScrapeCommittee(name=name, parent=self.chamber)
        return HouseCommitteeDetail(com, source=link)
