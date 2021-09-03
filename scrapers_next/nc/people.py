import attr

# import re
from spatula import HtmlListPage, HtmlPage, CSS, XPath

from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    party: str = ""
    # email: str = ""
    chamber: str = ""
    counties: str = ""


class LegDetail(HtmlPage):
    # input_type = PartialMember

    example_source = "https://www.ncleg.gov/Members/Biography/S/416"

    def process_page(self):

        # image = ("//img[contains(@src, '/photo')]").match_one(self.root).get("src")
        # print(image)

        # email
        try:
            email, legislative_assistant = XPath(
                "//a[contains(@href, 'mailto')]"
            ).match(self.root)
        except ValueError:
            email = XPath("//a[contains(@href, 'mailto')]").match_one(self.root)
        # print("EMAIL", email.text_content())
        # TODO: add legislative assistant name and email to extras
        #    '//div[contains(@class, "media-body")]//a[contains(@href, "member_bio")]'
        # "section/div[contains(@class,'large-8')]/div[contains(@class,'base')]"

        image = (
            XPath("//img[contains(@src, '/Members/MemberImage')]")
            .match_one(self.root)
            .get("src")
        )
        # print("IMAGE", image)

        # TODO: need capitol office address, office phone number, terms in senate (extras)

        # first grab mailing address
        address_header = XPath("//h6[@class='mt-3']").match_one(self.root)
        address = XPath(".//following-sibling::p").match(address_header)
        address = address[0].text_content() + "; " + address[1].text_content()
        print("address", address)

        # table = XPath("//div[@class='row mx-md-0']/div").match(self.root)
        # for ee in table:
        #     print("ee", ee.text_content())
        # TODO: where to get email from? idk
        __, terms, __, phone_number, __, assistant = XPath(
            "//div[@class='row mx-md-0']/div"
        ).match(self.root)
        # print('terms', terms.text_content())
        #    if contact.text_content().strip() == "Fax:":
        #         fax_number = (
        #             XPath(".//following-sibling::div")
        #             .match_one(contact)
        #             .text_content()
        #             .strip()
        #         )

        p = ScrapePerson(
            name=self.input.name,
            state="nc",
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=email.text_content(),
            image=image,
        )

        p.capitol_office.address = address
        p.capitol_office.voice = phone_number.text_content()

        # TODO: terms are spaced weird
        p.extras["terms in senate"] = (
            terms.text_content().replace("( ", "(").replace(" )", ")")
        )

        p.extras["represented counties"] = self.input.counties
        try:
            p.extras["legislative assistant"] = legislative_assistant.text_content()
            p.extras["legislative assistant email"] = legislative_assistant.get(
                "href"
            ).split(":")[1]
        except UnboundLocalError:
            pass

        p.add_source(self.source.url)
        p.add_source(self.input.url)

        for url in XPath(
            "//nav[contains(@class, 'nav nav-pills')]/a[@class='nav-item nav-link']"
        ).match(self.root):
            p.add_link(url.get("href"))

        return p


class LegList(HtmlListPage):
    selector = CSS("#memberTable tbody tr")

    def process_item(self, item):
        # try:
        #     name, district, district2, __, __, __ = CSS(
        #         ".pr-0 p"
        #     ).match(item)
        #     print("Name, district, district 2", name.text_content())
        #     url = name.get("href")

        #     print("URL", url)
        # except ValueError:
        #     name, district, district2, __, __, __, __ = CSS(
        #         ".pr-0 p"
        #     ).match(item)

        party, district, _, _, full_name, counties = item.getchildren()

        party = party.text_content().strip()
        party = dict(D="Democratic", R="Republican")[party]

        # name.text_content(), district.text_content(), counties.text_content()
        # image = CSS("img").match_one(image).get("src")

        # TODO: for full name: Sam Searcy (Resigned 1/6/21) and Sydney Batch

        # TODO: make sure Sam Searcy is skipped?

        # if full_name.text_content().strip()
        # full_name = full_name.text_content()
        print("FULL NAME", full_name.text_content())
        name = full_name.text_content()
        if "Resigned" in full_name.text_content():
            self.skip()
        elif "Appointed" in full_name.text_content():
            name = (
                full_name.text_content()
                .split("(Appointed")[0]
                .replace("\r\n", "")
                .strip()
            )
            print("FULL", full_name)

        p = PartialMember(
            name=name,
            # state="nc",
            party=party,
            district=district.text_content(),
            chamber=self.chamber,
            url=self.source.url,
            counties=counties.text_content()
            .strip()
            .replace("\r\n", "")
            .replace("\xa0", "")
            .replace("                        ", " ")
            # image=image,
            # email=email.text_content(),
        )

        # p.capitol_office.voice = phone.text_content()
        # p.add_source(self.source.url)
        # p.add_source(url)
        new_source = CSS("a").match_one(full_name)
        print("NEW SOURCE", new_source.get("href"))
        url = new_source.get("href")
        # url = CSS(".sorting_1 a").match(item)
        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/S"
    chamber = "upper"


class RepList(LegList):
    source = "https://www.ncleg.gov/Members/MemberList/H"
    chamber = "lower"
