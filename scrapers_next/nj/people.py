# import lxml.html
import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError

from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""


phone_pattern = re.compile(r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}")
fax_pattern = re.compile(r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}")

address_re = re.compile(
    (
        # Everyone's address starts with a room or street number
        r"(?:\d+)"
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

# TODO: before scrape, add p
# TODO: also add comments to explain what's happening here


# optional fax number parameter
# def process_address(details, phone_numbers, p, *fax_number):
def process_address(details, phone_numbers, p, fax_number=[]):

    # TODO: add p to parameters here

    phone_number_match = phone_pattern.findall(phone_numbers)
    # TODO: WHAT's going on with the asterisk before fax number
    # print("fax number in process", *fax_number)
    print("fax number in process", fax_number)

    print("phone number match", phone_number_match)
    match = address_re.findall(details)
    # print('match', address_re.findall(details))
    print("here is the match", match)
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
            print("new address: ", address)
            print("corresponding phone number", phone_number_match[i])

            # Often, there are fewer fax numbers than addresses or phone numbers
            try:
                # print("corresponding fax number: ", *fax_number[i])
                print("corresponding fax number2: ", fax_number[i])

                # does this work? below: no
                # fax_num = *fax_number[i]
                print("fax number without star", fax_number[i])
                p.add_office(
                    contact_type="District Office",
                    address=address,
                    voice=phone_number_match[i],
                    fax=fax_number[i],
                )
            except IndexError:
                p.add_office(
                    contact_type="District Office",
                    address=address,
                    voice=phone_number_match[i]
                    # TODO: add fax here if there IS ONE ONLY
                )

            # TODO: if there is only one address, then just put in District Office


class LegDetail(HtmlPage):
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=328"
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=304"

    # source for multiple offices and multiple phone numbers
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=371"

    # example source for fax numbers
    example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=406"
    #
    # TODO: add source

    def process_page(self):

        # party = CSS("i").match(self.root)[0].getchildren()

        party = CSS("i").match(self.root)[0].text_content().strip()
        try:
            position = CSS("i font").match_one(self.root).text_content().strip()
            party = party.replace(position, "")
            # party = CSS("i").match(self.root)[0].text_content().strip()
            # print('okay here"s the party', party)
        except SelectorError:
            # party = CSS("i").match(self.root)[0].text_content().strip()
            pass

        if re.search("(D)", party):
            party = "Democrat"
        elif re.search("(R)", party):
            party = "Republican"
        else:
            # TODO: i don't think this is it..but must warn
            # self.warn("Not a major party, please update")
            print(party)

        print("PARTY: ", party)

        # PHONE NUMBERS
        #
        # this only works if there's no position under the name UGH
        # phone_numbers = CSS("font").match(self.root)[31].text_content()
        # phone_numbers = CSS("font").match(self.root)[30].text_content()
        phone_numbers = XPath("//font[@size='2']").match(self.root)[10].text_content()
        print("phone numbers: ", phone_numbers)

        # TODO: i think district office will just be one item all the time
        # TODO: also not sure if district_office will pick up everyone else's address the same way...maybe sometimes there's another p tag...
        district_office = CSS("p").match(self.root)[13].getchildren()
        # print("district office", district_office)

        image = (
            XPath("//img[contains(@src, 'memberphotos')]")
            .match_one(self.root)
            .get("src")
        )
        print('here"s the image', image)

        district = CSS("font b").match(self.root)[26].text_content().split(" ")[1]
        print("district number: ", district)

        # TODO: email (hardcode the emails?)
        # All emails should still be AsmLAST@njleg.org and SenLAST@njleg.org - many reps have these emails on their personal pages

        # MAKE SURE this works for Richard J. Codey
        name_email = self.input.name.split("\xa0")
        print("name email", name_email)
        name_email2 = name_email[len(name_email) - 1]

        if self.input.chamber == "upper":
            email = f"Sen{name_email2}@njleg.org"
        elif self.input.chamber == "lower":
            email = f"Asm{name_email2}@njleg.org"
        print("email: ", email)

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

        # Q: is it okay to just associate fax numbers with the first address?? (everything ive seen so far does this)
        try:
            # TODO: WHY does this run for pages that don't have A FAX NUMBER
            fax_match = fax_pattern.findall(
                XPath("//font[@size='2']").match(self.root)[12].text_content()
            )
            print("fax match", fax_match)

            for okay in district_office:
                address = okay.text_content()
                if fax_match:
                    process_address(address, phone_numbers, p, fax_number=fax_match)
                else:
                    process_address(address, phone_numbers, p)
            # if there is a fax number:
            # TODO: if statement above along with sending to process_address (nested inside if statement)
        except SelectorError:
            pass

        return p


class LegList(HtmlListPage):
    source = "https://www.njleg.state.nj.us/members/abcroster.asp"

    def process_item(self, item):

        print(item.text_content())
        name = item.text_content()
        p = PartialMember(name=name, chamber=self.chamber, url=self.source.url)

        return LegDetail(p, source=item.get("href"))


# attempt: for every font color...
class SenList(LegList):
    # bottom works for uglier webpage
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
