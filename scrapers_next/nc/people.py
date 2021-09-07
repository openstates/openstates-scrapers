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
    appointment: str = ""


class LegDetail(HtmlPage):
    input_type = PartialMember

    example_source = "https://www.ncleg.gov/Members/Biography/S/416"

    def process_page(self):

        try:
            email, legislative_assistant = XPath(
                "//a[contains(@href, 'mailto')]"
            ).match(self.root)
        except ValueError:
            email = XPath("//a[contains(@href, 'mailto')]").match_one(self.root)

        image = (
            XPath("//img[contains(@src, '/Members/MemberImage')]")
            .match_one(self.root)
            .get("src")
        )

        # if there's no legislative address, but there's a mailing address:
        # capital office is mailing address
        # if there's a legislative address, and a mailing address:
        # capital office is legislative address

        # TODO: where to get email from? idk
        # if self.input.chamber == 'upper'
        # try:
        #     __, terms, __, phone_number, __, assistant = XPath("//div[@class='row mx-md-0']/div").match(self.root)
        # except ValueError:
        #     # this is for Representatives
        #     pass
        # try:
        # __, terms, __, occupation, __, phone_number, __, military, __, __ = XPath("//div[@class='row mx-md-0']/div").match(self.root)

        table = XPath("//div[@class='row mx-md-0']/div").match(self.root)
        if len(table) == 6:
            __, terms, __, phone_number, __, assistant = table
        elif len(table) == 10:
            __, terms, __, occupation, __, phone_number, __, military, __, __ = table
        else:
            __, terms, __, occupation, __, phone_number, __, __ = table

        # print("UM THE NAME PASSED", self.input.name)

        p = ScrapePerson(
            name=self.input.name,
            state="nc",
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=email.text_content(),
            image=image,
        )

        address_header = XPath("//h6[@class='mt-3']").match(self.root)
        # the first address will either be legislative office or mailing address
        # if there's only one address, it's mailing address (i think...?)
        # if there are two addresses, the first addy is legislative office

        # if len(address_header) == 1 and address_header[0].text_content() == "Mailing Address:":
        address = XPath(".//following-sibling::p").match(address_header[0])
        address = address[0].text_content() + "; " + address[1].text_content()
        # print("address", address)

        try:
            if address_header[1].text_content() == "Mailing Address:":
                mailing_address = XPath(".//following-sibling::p").match(
                    address_header[0]
                )
                mailing_address = (
                    mailing_address[0].text_content()
                    + "; "
                    + mailing_address[1].text_content()
                )
                p.extras["mailing address"] = mailing_address
        except IndexError:
            pass

        p.capitol_office.address = address
        p.capitol_office.voice = phone_number.text_content()

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

        try:
            p.extras["occupation"] = occupation.text_content()
        except UnboundLocalError:
            pass

        try:
            p.extras["military experience"] = military.text_content()
        except UnboundLocalError:
            pass

        if self.input.appointment:
            p.extras["appointment date"] = self.input.appointment

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
        appointment = ""

        party, district, _, _, full_name, counties = item.getchildren()

        party = party.text_content().strip()
        party = dict(D="Democratic", R="Republican")[party]

        # TODO: for full name: Sam Searcy (Resigned 1/6/21) and Sydney Batch

        # TODO: make sure Sam Searcy is skipped?
        # print("FULL NAME", full_name.text_content())
        name = full_name.text_content()
        # print("NAME", name)
        if (
            "Resigned" in full_name.text_content()
            or "Deceased" in full_name.text_content()
        ):
            self.skip()
        elif "Appointed" in full_name.text_content():
            # print("REached here!!!")
            # appointment = full_name.text_content().replace("(", "")
            # name = (
            #     full_name.text_content()
            #     .split("(Appointed")[0]
            #     .replace("\r\n", "")
            #     .strip()
            # )
            name, appointment = full_name.text_content().split("(Appointed")
            # name = name.replace("\r\n", "").strip()
            appointment = appointment.replace(")", "").replace("\r\n", "").strip()
            # print("FULL", full_name)
            print("appointment", appointment)
        name = name.replace("\r\n", "").strip()
        # print("HELLOOO", name)

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
            .replace("                        ", " "),
            appointment=appointment,
        )
        # new_source =
        # print("NEW SOURCE", new_source.get("href"))
        url = CSS("a").match_one(full_name).get("href")
        # url = CSS(".sorting_1 a").match(item)
        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/S"
    chamber = "upper"


class RepList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/H"
    chamber = "lower"

    # https://www.ncleg.gov/Members/Biography/H/764: has occupation and legislative office (which are the same?)
