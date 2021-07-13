# import lxml.html
import attr
from spatula import HtmlListPage, HtmlPage, CSS, XPath

# from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    # url: str
    # district: int
    # image: str
    # party: str = ""


class LegDetail(HtmlPage):
    example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=328"
    # add source


class LegList(HtmlListPage):
    # source = "https://www.njleg.state.nj.us/members/abcroster.asp"
    source = "https://www.njleg.state.nj.us/members/roster.asp"
    # add source
    # email(?), image, a lot of extra info
    # attempt: just go on individual page and get the info...

    def process_item(self, item):

        print(item.getchildren())
        # print(item.get_children())
        # print('hello item', item)
        # print(item.text_content().strip())

        print("hi")

        # COMMENT OUT THIS PART (3 lines)
        # name = item.text_content().strip()
        # for item in XPath('..//preceding-sibling:: p').match(self.root):
        #     print('item', item.text_content())
        # print(name)

        print(item.text_content())
        # sibling = XPath("..//preceding-sibling::td[1]").match(self.root)
        # print(sibling)
        # print(XPath('./following-sibling::')))

        # print('hi')

        # p = PartialMember(name=name, state="nj", chamber=self.chamber)
        # what's on this page: state, name, chamber, party, district office address (there are sometimes multiple), phone number

        # individual people pages
        # return LegDetail(p, source=item.get("href"))


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
    # selector = XPath("/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()<=40]")

    # selector = CSS("body table td[@colspan='5']")

    # to do with new link
    # selector = XPath("//a[contains(@href, 'BIO')][position()<=40]")
    selector = XPath(
        "//html/body/form/div/table/tbody/tr[6]/td/div/p[1]/table/tbody/tr[4]/td/table"
    )

    # selector = XPath("//*[@id='Bills']/div/table/tbody/tr[6]/td/div/p[1]/table/tbody/tr[4]/td/table")
    # selector = XPath("//body//table")
    chamber = "upper"


class RepList(LegList):
    selector = CSS("", num_items=80)
    chamber = "lower"
