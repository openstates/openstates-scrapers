import re
from spatula import XmlListPage, URL, XPath
from .common.people import Person, PeopleWorkflow


def clean_name(name):
    name = re.sub(r"\s+", " ", name)
    name = name.strip()
    return name.title()


ELEMENTS = (
    "FirstName",
    "MiddleName",
    "LastName",
    "EMail",
    "Phone",
    "District",
    "Party",
    "Building",
    "Room",
)


def _get_if_exists(item, elem):
    val = item.xpath(f"./{elem}/text()")
    if val:
        return str(val[0])


class Legislators(XmlListPage):
    session_num = "32"
    source = URL(
        "http://www.legis.state.ak.us/publicservice/basis/members"
        f"?minifyresult=false&session={session_num}",
        headers={"X-Alaska-Legislature-Basis-Version": "1.4"},
    )
    selector = XPath("//Member/MemberDetails")

    def process_item(self, item):
        item_dict = {elem: _get_if_exists(item, elem) for elem in ELEMENTS}
        chamber = item.attrib["chamber"]
        code = item.attrib["code"].lower()

        person = Person(
            name="{FirstName} {LastName}".format(**item_dict),
            given_name=item_dict["FirstName"],
            family_name=item_dict["LastName"],
            state="ak",
            party=item_dict["Party"],
            chamber=("upper" if chamber == "S" else "lower"),
            district=item_dict["District"],
            image=f"http://akleg.gov/images/legislators/{code}.jpg",
            email=item_dict["EMail"],
        )
        person.add_link(
            "http://www.akleg.gov/basis/Member/Detail/{}?code={}".format(
                self.session_num, code
            )
        )
        person.add_source("http://w3.akleg.gov/")

        if item_dict["Phone"]:
            phone = "907-" + item_dict["Phone"][0:3] + "-" + item_dict["Phone"][3:]
            person.capitol_office.voice = phone

        if item_dict["Building"] == "CAPITOL":
            person.capitol_office.address = (
                "State Capitol Room {}; Juneau, AK, 99801".format(item_dict["Room"])
            )

        return person


legislators = PeopleWorkflow(Legislators)
