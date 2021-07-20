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


# TODO: add comments to explain what's going on here
phone_pattern = re.compile(r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}")
fax_pattern = re.compile(r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}")
# + "(.+?" + ")"
# phone_pattern2 = re.compile(r"?\(?\d+\)?[- ]?\d{3}[-.]\d{4}")

address_re = re.compile(
    (
        # every rep's address starts with a room or street number
        r"(?:\d+)"
        # just about anything can follow:
        + ".+?"
        # state and zip code
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


def process_address(details, phone_numbers):
    # TODO: add p to parameters here

    phone_number_match = phone_pattern.findall(phone_numbers)

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

            # p.add_office(
            #     contact_type="District Office",
            #     address=address,
            #     voice = phone_number_match[i]

            # )


class LegDetail(HtmlPage):
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=328"
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=304"

    # source for multiple offices and multiple phone numbers
    # example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=371"

    # example source for fax numbers
    example_source = "https://www.njleg.state.nj.us/members/BIO.asp?Leg=406"

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

        if re.search("(D)", party):
            party = "Democrat"
        elif re.search("(R)", party):
            party = "Republican"
        else:
            # TODO: i don't think this is it..but must warn
            # self.warn("Not a major party, please update")
            print(party)

        print("R or D", party)

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
        print("district office", district_office)

        # p = ScrapePerson(
        #     name=self.input.name,
        #     chamber = self.input.chamber,
        # )

        # p.add_source(self.input.url)
        # p.add_source(self.source.url)

        for okay in district_office:
            # directly targeting the font tag
            print("okay", okay.text_content())
            address = okay.text_content()
            process_address(address, phone_numbers)

        # for thing in phone_numbers:
        #     print('thing', thing.text_content())
        # TODO: for fax numbers, make sure that it is numbers (may not have to do this, since the plan is to not scrape email and just hardcode it, so if there is another <font> then that means there is a fax number--do try, except)
        # Q: is it okay to just associate fax numbers with the first address?? (everything ive seen so far does this)
        try:
            # fax = XPath("//font[@size='2']").match(self.root)[12].text_content()
            # print('fax number', fax)
            # TODO: WHY does this run for pages that don't have A FAX NUMBER
            fax_match = fax_pattern.findall(
                XPath("//font[@size='2']").match(self.root)[12].text_content()
            )
            print("fax match", fax_match)
            # if fax_match:
            # if there is a fax number:
        except SelectorError:
            pass


# TODO: email (hardcode the emails?)


class LegList(HtmlListPage):
    source = "https://www.njleg.state.nj.us/members/abcroster.asp"
    # source = "https://www.njleg.state.nj.us/members/roster.asp"
    # add source
    # email(?), image, a lot of extra info
    # attempt: just go on individual page and get the info...

    def process_item(self, item):

        print(item.text_content())
        name = item.text_content()
        p = PartialMember(name=name, chamber=self.chamber, url=self.source.url)
        # what's on this page: state, name, chamber, party, district office address (there are sometimes multiple), phone number

        # individual people pages
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
