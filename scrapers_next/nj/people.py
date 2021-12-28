import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""


phone_fax_pattern = re.compile(r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}")

address_re = re.compile(
    (
        # Everyone's address starts with a room or street number
        # (sometimes written out in words) or building name
        r"(?:\d+|.+?)"
        # just about anything can follow:
        + ".+?"
        # then, state and zip code
        + "(?:"
        + "|".join(
            [r" +(?:NJ|New Jersey)(?: +0\d{4})?", r"(?:NJ|New Jersey),? +0\d{4}"]
        )
        + ")"
    ),
    flags=re.DOTALL | re.IGNORECASE,
)


def process_address(details, phone_numbers, p, fax_number=[]):

    phone_number_match = phone_fax_pattern.findall(phone_numbers)

    match = address_re.findall(details)

    if match is not None:
        num_of_addresses = range(len(match))

        for i in num_of_addresses:
            address = re.sub(
                " +$",
                "",
                match[i]
                .replace("\r", "")
                .replace("\n", " ")
                .replace("  ", " ")
                .replace("                       ", " ")
                .strip(),
                flags=re.MULTILINE,
            )

            # Some office addresses don't have phone numbers
            phone = ""
            try:
                phone = phone_number_match[i]
            except IndexError:
                pass

            # Often, there are fewer fax numbers than addresses or phone numbers,
            # or fewer phone numbers than addresses
            try:
                fax = fax_number[i]

                # For the first address in the list
                if i == 0:
                    # There is a phone number for this address
                    if phone != "":
                        p.district_office.address = address
                        p.district_office.voice = phone
                        p.district_office.fax = fax
                else:
                    if phone != "":
                        p.add_office(
                            classification="district",
                            address=address,
                            voice=phone,
                            fax=fax_number[i],
                        )
                    else:
                        p.add_office(
                            classification="district",
                            address=address,
                            fax=fax_number[i],
                        )
            except IndexError:
                if i == 0:
                    if phone != "":
                        p.district_office.address = address
                        p.district_office.voice = phone_number_match[i]
                    else:
                        p.district_office.address = address
                else:
                    if phone != "":
                        p.add_office(
                            classification="district", address=address, voice=phone
                        )
                    else:
                        p.add_office(
                            classification="district",
                            address=address,
                        )


class LegDetail(HtmlPage):
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=328"
    example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=406"

    def process_page(self):
        party = CSS("i").match(self.root)[0].text_content().strip()

        # Checking for if this rep has a specific position
        position = ""
        try:
            position = CSS("i font").match_one(self.root).text_content().strip()
            party = party.replace(position, "")

        except SelectorError:
            pass

        if re.search("(D)", party):
            party = "Democrat"
        elif re.search("(R)", party):
            party = "Republican"
        else:
            self.logger.warning(f"the party {party} must be included")

        phone_numbers = XPath("//font[@size='2']").match(self.root)[10].text_content()

        district_office = CSS("p").match(self.root)[13].getchildren()

        image = (
            XPath("//img[contains(@src, 'memberphotos')]")
            .match_one(self.root)
            .get("src")
        )

        district = CSS("font b").match(self.root)[26].text_content().split(" ")[1]

        # All emails should still be AsmLAST@njleg.org and SenLAST@njleg.org -
        # many reps have these emails on their personal pages
        fullname_email = self.input.name.split("\xa0")
        lastname_email = fullname_email[len(fullname_email) - 1]

        if self.input.chamber == "upper":
            email = f"Sen{lastname_email}@njleg.org"
        elif self.input.chamber == "lower":
            email = f"Asm{lastname_email}@njleg.org"

        p = ScrapePerson(
            name=self.input.name,
            state="nj",
            chamber=self.input.chamber,
            party=party,
            image=image,
            district=district,
            email=email,
        )

        p.add_source(self.input.url)
        p.add_source(self.source.url)
        if position != "":
            p.extras["role"] = position.replace("(", "").replace(")", "").strip()

        try:
            fax_match = phone_fax_pattern.findall(
                XPath("//font[@size='2']").match(self.root)[12].text_content()
            )

            for okay in district_office:
                address = okay.text_content()
                if fax_match:
                    process_address(address, phone_numbers, p, fax_number=fax_match)
                else:
                    process_address(address, phone_numbers, p)

        except SelectorError:
            pass

        return p


class LegList(HtmlListPage):
    source = "https://www.njleg.state.nj.us/members/abcroster.asp"

    def process_item(self, item):
        name = item.text_content()
        p = PartialMember(name=name, chamber=self.chamber, url=self.source.url)

        return LegDetail(p, source=item.get("href"))


class SenList(LegList):
    selector = XPath(
        "/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()<=40]",
        num_items=40,
    )
    chamber = "upper"


class RepList(LegList):
    selector = XPath(
        "/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()>40]",
        num_items=80,
    )
    chamber = "lower"
