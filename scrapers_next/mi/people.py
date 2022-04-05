import re
from spatula import HtmlListPage, CSS, URL
from openstates.models import ScrapePerson


def split_name(name):
    commas = name.count(",")
    if commas == 0:
        first, last = name.split(" ", 1)  # special case for one legislator right now
    elif commas == 1:
        last, first = name.split(", ")
    else:
        raise ValueError(name)

    if re.search("Dr.", first):
        first = re.sub("Dr.", "", first)

    return {"given_name": first, "family_name": last, "name": f"{first} {last}"}


def ord_suffix(str_num):
    num = int(str_num) % 100
    if 4 <= num <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")


class Senators(HtmlListPage):
    source = URL("https://senate.michigan.gov/senatorinfo_list.html", verify=False)
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

        p = ScrapePerson(
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


class Representatives(HtmlListPage):
    source = "https://www.house.mi.gov/AllRepresentatives"
    selector = CSS("#allreps .list-item", num_items=110)
    office_names = {
        "SHOB": "South House Office Building",
        "NHOB": "North House Office Building",
        "CB": "Capitol Building",
    }

    def process_item(self, item):
        if "Vacant" in item.text_content():
            self.skip("vacant")
        link = item.xpath(".//a")[0]
        url = link.get("href")
        (
            name,
            party,
            district,
        ) = re.match(r"\s+([^\(]+)\((\w+)\)\s+District-(\d+)", link.text).groups()

        contact = item.getchildren()[1].getchildren()[0:3]
        office = contact[0].text_content().strip()
        phone = contact[1].text_content().strip()
        email = contact[2].text_content().strip()

        p = ScrapePerson(
            **split_name(name),
            state="mi",
            chamber="lower",
            district=district,
            party=party,
            email=email,
        )
        if url.startswith("http:/r"):
            url = url.replace("http:/", "http://")
        p.add_link(url)
        p.add_source(self.source.url)
        p.capitol_office.voice = phone
        p.capitol_office.address = office
        return p
