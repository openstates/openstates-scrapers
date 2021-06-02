from spatula import HtmlListPage, CSS
from ..common.people import Person, PeopleWorkflow


def split_name(name):
    commas = name.count(",")
    if commas == 0:
        first, last = name.split(" ", 1)  # special case for one legislator right now
    elif commas == 1:
        last, first = name.split(", ")
    else:
        raise ValueError(name)
    return {"given_name": first, "family_name": last, "name": f"{first} {last}"}


def ord_suffix(str_num):
    num = int(str_num) % 100
    if 4 <= num <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")


class SenList(HtmlListPage):
    source = "https://senate.michigan.gov/senatorinfo_list.html"
    selector = CSS(".table tbody tr", num_items=38)
    PARTY_MAP = {"Rep": "Republican", "Dem": "Democratic"}

    def process_item(self, item):
        member, party, district, contact_link, phone, office = item.getchildren()

        name = member.text_content()
        district = district.text_content()

        # skip vacant districts
        if "Interim District" in name:
            self.skip()

        # each of these <td> have a single link
        leg_url = CSS("a").match_one(member).get("href")
        contact_url = CSS("a").match_one(contact_link).get("href")
        # construct this URL based on observation elsewhere on senate.michigan.gov
        image_url = (
            f"https://senate.michigan.gov/_images/{district}{ord_suffix(district)}.jpg"
        )

        p = Person(
            **split_name(name),
            state="mi",
            chamber="upper",
            district=district,
            party=self.PARTY_MAP[party.text],
            image=image_url,
        )
        p.capitol_office.voice = str(phone.text_content())
        p.capitol_office.address = str(office.text_content())
        p.add_source(self.source.url)
        p.add_link(leg_url)
        p.add_link(contact_url, note="Contact")
        return p


class RepList(HtmlListPage):
    source = "https://www.house.mi.gov/MHRPublic/frmRepListMilenia.aspx?all=true"
    selector = CSS("#grvRepInfo tr", num_items=111)
    office_names = {
        "SHOB": "South House Office Building",
        "NHOB": "North House Office Building",
        "CB": "Capitol Building",
    }

    def process_item(self, item):
        website, district, name, party, office, phone, email = item.getchildren()

        # skip header row
        if website.tag == "th":
            self.skip()

        office = office.text_content()
        for abbr, full in self.office_names.items():
            office = office.replace(abbr, full)

        p = Person(
            name=name.text_content(),
            state="mi",
            chamber="lower",
            district=district.text_content().lstrip("0"),
            party=party.text_content(),
            email=email.text_content(),
        )
        p.add_link(CSS("a").match_one(website).get("href"))
        p.add_source(self.source.url)
        p.capitol_office.voice = phone.text_content()
        p.capitol_office.address = office
        return p


senators = PeopleWorkflow(SenList)
reps = PeopleWorkflow(RepList)
