# import lxml.html
import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError

# from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""
    # district: int
    # image: str
    # party: str = ""


class LegDetail(HtmlPage):
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=328"
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=304"

    # source for multiple offices and multiple phone numbers
    example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=371"

    # TODO: add source

    def process_page(self):
        # print('self', self.input.name)

        # TODO: multiple office addresses sometimes
        # party = CSS("i").match(self.root)[0].text_content().strip()
        party = CSS("i").match(self.root)[0].getchildren()

        party = CSS("i").match(self.root)[0].text_content().strip()
        try:
            position = CSS("i font").match_one(self.root).text_content().strip()
            party = party.replace(position, "")
            # party = CSS("i").match(self.root)[0].text_content().strip()
            # print('okay here"s the party', party)
        except SelectorError:
            # party = CSS("i").match(self.root)[0].text_content().strip()
            pass

        # print('party', party)
        # for what in party:
        #     print(what.text_content())

        # print('okay', party)
        if re.search("(D)", party):
            party = "Democrat"
        elif re.search("(R)", party):
            party = "Republican"
        else:
            # TODO: i don't think this is it..but must warn
            # self.warn("Not a major party, please update")
            print(party)

        print("R or D", party)

        # TODO: there are multiple district offices sometimes: after every two consecutive br tags
        # or maybe after "NJ" and then 5 numbers for zip code?
        # district_office = CSS("p").match(self.root)[13].text_content().strip()
        district_office = CSS("p").match(self.root)[13].getchildren()
        print("all addresses", district_office)
        for what in district_office:
            children_p_tag = what.getchildren()

            # this shows a bunch of br tags in an array
            print("children of p tag", children_p_tag)
            for child in children_p_tag:
                print("single child", child.text_content())
            # children_of_children = children_p_tag.getchildren()
            # print('children of children', children_of_children)
            # next = what.text_content()
            # print('next', next)

            # for element in next:
            #     print('element', element)
            # okay = next.text_content().split("NJ")
            # print('here', okay)
            # for element in okay:
            #     print('replace', element.replace('\r\n', "").strip())

        print("office address", district_office)
        # for what in CSS("p").match(self.root):
        # print('okay', what.text_content())

        # print(district_office)

        # p = ScrapePerson(
        #     name = self.input.name,
        #     state = 'nj',

        # )


#  name=self.input.name,
#             state="ia",
#             chamber=self.input.chamber,
#             party=self.input.party,
#             district=self.input.district,
#             email=self.input.email,
#             image=image,


class LegList(HtmlListPage):
    source = "https://www.njleg.state.nj.us/members/abcroster.asp"
    # source = "https://www.njleg.state.nj.us/members/roster.asp"
    # add source
    # email(?), image, a lot of extra info
    # attempt: just go on individual page and get the info...

    def process_item(self, item):

        # print(item.getchildren())
        # print(item.get_children())
        # print('hello item', item)
        # print(item.text_content().strip())

        # print("hi")

        # COMMENT OUT THIS PART (3 lines)
        # name = item.text_content().strip()
        # for item in XPath('..//preceding-sibling:: p').match(self.root):
        #     print('item', item.text_content())
        # print(name)

        print(item.text_content())
        name = item.text_content()
        # sibling = XPath("..//preceding-sibling::td[1]").match(self.root)
        # print(sibling)
        # print(XPath('./following-sibling::')))

        # print('hi')

        p = PartialMember(name=name, chamber=self.chamber, url=self.source.url)
        # what's on this page: state, name, chamber, party, district office address (there are sometimes multiple), phone number

        # individual people pages
        return LegDetail(p, source=item.get("href"))


# attempt: for every font color...
class SenList(LegList):
    # selector = CSS("table tr a")
    # print("hi there", XPath("//table[3]"))
    # selector = XPath("//table[1]//tr[1]/td")
    # print("hello", selector)
    # selector = CSS("body td div font")

    # selector = CSS("html body table")

    # selector = XPath("/html/body/table/tr[6]//p//a")

    # selector = XPath("/html/body/table/tbody/tr[6]/td/table/tbody/tr/td[2]/p[2]/b[1]/a")
    # /html/body/table/tbody/tr[6]/td/table/tbody/tr/td[2]/p[2]/b[1]/a
    # /html/body/table/tbody/tr[6]/td/table/tbody/tr/td[2]/p[2]/b[1]/a

    # bottom works for uglier webpage
    selector = XPath(
        "/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()<=40]",
        num_items=40,
    )

    # selector = CSS("body table td[@colspan='5']")

    # to do with new link
    # selector = XPath("//a[contains(@href, 'BIO')][position()<=40]")
    # selector = XPath(
    #     "//html/body/form/div/table/tbody/tr[6]/td/div/p[1]/table/tbody/tr[4]/td/table"
    # )

    # selector = XPath("//*[@id='Bills']/div/table/tbody/tr[6]/td/div/p[1]/table/tbody/tr[4]/td/table")
    # selector = XPath("//body//table")
    chamber = "upper"


class RepList(LegList):
    selector = XPath(
        "/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()>40]",
        num_items=80,
    )
    chamber = "lower"
