from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.people.models.committees import ScrapeCommittee

# class CommitteeList(HtmlListPage):
#     def process_item(self, item):
#         # return item
#         name = item.text_content().strip()
#         return name
#         # return CSS(item.getchildren())


#         p = ScrapeCommittee(
#             name = name,
#             parent = self.chamber
#         )
#         return p


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        # com = self.input
        # com.add_source(self.source.url)

        # for role in CSS(".align-self-center b").match(self.root):
        #     print(CSS(".align-self-center b").match(self.root))
        #     name = role.text_content()
        #     # name = CSS("h5 a").text_content()
        #     com.add_member(name, "Chair")

        leadership_role = XPath("//div[contains(@class, media-body)]/b/text()").match(
            self.root
        )
        for position in leadership_role:
            role = position
            print("role", role)
            # com.add_member("Tom", role)
        print(CSS(".pl-2 .align-self-center h5 a").match(self.root)[5].text_content())

        section = CSS(".pl-2").match(self.root)[1]
        print("section name", section)
        # and then for each person in the members?

        # new idea inspired by old scraper
        # for p in CSS(".media-body").match(self.root):
        # print(XPath('//div[@id="members"]//a[contains(@href, "member_bio")]//b/text()'))
        # print(name)

        # print(XPath('//div[contains(@class, media-body]//a[contains(@href, "member_bio")]//b/text()'))

        for link in XPath(
            '//div[contains(@class, "media-body")]//a[contains(@href, "member_bio")]'
        ).match(self.root):
            name = link.text_content()
            if name:
                try:
                    position = XPath("..//preceding-sibling::b/text()").match(link)
                except SelectorError:
                    position = "member"
                # print(position)
                # if position is None:
                #     position = "member"
                # else:
                #     position = "chair"
                # if position[0] == "Chair":
                #     position="Chair"
                # elif position[0] == "Vice Chair":
                #     position = "vice chair"
                # else:

                # for role in position:
                #     position_str = ''
                #     position_str += role
                #     position_str.lower()
                # if not position:
                #     position="member"
                # elif position[0] == "Chair":
                #     position="chair"
            print(name, position)

        # leadership_role = XPath("//div[contains(@class, media-body)]/b/text()").match(self.root)

        # original plan: for each person
        # if there is a b tag

        # for each row pl-2...

        # for the first row pl-2, do this
        # for the second row pl-2 do that

        # for p in CSS(".media-body").match(self.root):
        # for each blurb
        # leadership_role = XPath("/html/body/div[1]/div[3]/div/div[2]/div[1]/div[1]/div[1]/div/div[2]/b/text").text_content()
        # print(leadership_role)

        # com.add_member(name, role)

        # for each membership role ("chair, vice chair, ranking minority member")
        # role = the above
        # name = h5 a b
        # and then??

        # //*[@id="legContainerMain"]/div/div[2]/div[1]/div[1]/div[1]/div/div[2]/b
        # if leadership_role:
        #     role = leadership_role.text_content()

        # else:
        #     role = "member"

        # com.add_member("Tim", role)

        # for membership_type in CSS(".col-lg-9 ")
        # members = [
        # p.text_content() for p in CSS(".align-self-center").match()
        # ]
        # print("self.root", self.root)
        # return com


#  todo: subcommittees!
class SenateCommitteeList(HtmlListPage):
    selector = CSS(" .card .list-group-flush .d-flex a")
    source = "https://www.senate.mn/committees"
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()

        com = ScrapeCommittee(name=name, parent=self.chamber)
        com.add_source(self.source.url)
        # print(item.get("href"))
        # print(self.source.url)
        # print("self", self)
        # self: SenateCommitteeList(source-https://www.senate.mn/committees)
        return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
    selector = CSS("list-group-flush list-group-item")
    source = "https://www.house.leg.state.mn.us/committees"
    chamber = "lower"
