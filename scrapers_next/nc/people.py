import attr
from spatula import HtmlListPage, HtmlPage, CSS, XPath
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    party: str = ""
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
            try:
                email = XPath("//a[contains(@href, 'mailto')]").match_one(self.root).text_content()
            except Exception:
                email = ""

        image = (
            XPath("//img[contains(@src, '/Members/MemberImage')]")
            .match_one(self.root)
            .get("src")
        )

        table = XPath("//div[@class='row mx-md-0']/div").match(self.root)

        # there are different combinations of information the page can have
        if len(table) == 6:
            __, terms, __, main_phone, __, assistant = table
        elif len(table) == 10:
            __, terms, __, occupation, __, main_phone, __, military, __, __ = table
        else:
            __, terms, __, occupation, __, main_phone, __, __ = table

        p = ScrapePerson(
            name=self.input.name,
            state="nc",
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=email,
            image=image,
        )

        address_header = XPath("//h6[@class='mt-3']").match(self.root)

        address = XPath(".//following-sibling::p").match(address_header[0])
        address = address[0].text_content() + "; " + address[1].text_content()
        main_phone = main_phone.text_content().replace("\r\n", "").strip()

        # representatives have both legislative office addresses and mailing addresses,
        # while senators only have mailing addresses
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
                office_number = (
                    XPath(".//preceding-sibling::p[1]")
                    .match_one(address_header[1])
                    .text_content()
                    .replace("\r\n", "")
                    .strip()
                )

                # some reps have main phones and capitol office phones,
                # and senators only have capitol office phones
                if office_number != main_phone:
                    p.capitol_office.voice = office_number
                    p.extras["main phone"] = main_phone
                else:
                    p.capitol_office.voice = main_phone
        except IndexError:
            p.capitol_office.voice = main_phone

        p.capitol_office.address = address

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

        name = full_name.text_content()
        if (
            "Resigned" in full_name.text_content()
            or "Deceased" in full_name.text_content()
        ):
            self.skip()
        elif "Appointed" in full_name.text_content():
            name, appointment = full_name.text_content().split("(Appointed")
            appointment = appointment.replace(")", "").replace("\r\n", "").strip()
        name = name.replace("\r\n", "").strip()

        p = PartialMember(
            name=name,
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

        url = CSS("a").match_one(full_name).get("href")
        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/S"
    chamber = "upper"


class RepList(LegList):
    source = "https://www.ncleg.gov/Members/MemberTable/H"
    chamber = "lower"
