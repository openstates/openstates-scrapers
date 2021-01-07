#!/usr/bin/env python
from openstates.scrape import Person, Scraper, Organization
from .utils import open_csv


HEADERS = [
    "dist",
    "office code",
    "district number",
    "designator code",
    "first name",
    "middle initial",
    "last name",
    "suffix",
    "commonly used name",
    "home street address",
    "home city",
    "home state",
    "home zip code",
    "home phone",
    "capitol street address",
    "capitol city",
    "capitol phone",
    "room",
    "room number",
    "committees chaired",
    "committees vice chaired",
    "ranking member",
    "committee member1",
    "senator/representative",
    "party",
    "title",
    "gender",
    "business phone",
    "email",
    "fax",
    "prison",
    "URL",
    "committee codes",
]


class CTPersonScraper(Scraper):
    def scrape(self):
        # chambers = [chamber] if chamber is not None else ['upper', 'lower']
        leg_url = "ftp://ftp.cga.ct.gov/pub/data/LegislatorDatabase.csv"
        page = self.get(leg_url)

        committees = {}

        # Ensure that the spreadsheet's structure hasn't generally changed
        _row_headers = page.text.split("\r\n")[0].replace('"', "").split(",")
        assert _row_headers == HEADERS, "Spreadsheet structure may have changed"

        page = open_csv(page)
        for row in page:

            chamber = {"H": "lower", "S": "upper"}[row["office code"]]

            district = row["dist"].lstrip("0")
            assert district.isdigit(), "Invalid district found: {}".format(district)

            name = row["first name"]
            mid = row["middle initial"].strip()
            if mid:
                name += " %s" % mid
            name += " %s" % row["last name"]
            suffix = row["suffix"].strip()
            if suffix:
                name += " %s" % suffix

            party = row["party"]
            if party == "Democrat":
                party = "Democratic"

            leg = Person(primary_org=chamber, name=name, district=district, party=party)

            legislator_url = row["URL"].replace("\\", "//").strip()
            if legislator_url != "":
                if not legislator_url.startswith("http"):
                    legislator_url = "http://"
                leg.add_link(legislator_url)

            leg.add_party(party=party)

            office_address = "%s\nRoom %s\nHartford, CT 06106" % (
                row["capitol street address"],
                row["room number"],
            )
            # extra_office_fields = dict()
            email = row["email"].strip()
            if "@" not in email:
                if not email:
                    email = None
                elif email.startswith("http://") or email.startswith("https://"):
                    # extra_office_fields['contact_form'] = email
                    email = None
                else:
                    raise ValueError("Problematic email found: {}".format(email))
            if office_address.strip():
                leg.add_contact_detail(
                    type="address", value=office_address, note="Capitol Office"
                )
            if row["capitol phone"].strip():
                leg.add_contact_detail(
                    type="voice", value=row["capitol phone"], note="Capitol Office"
                )
            if email:
                leg.add_contact_detail(type="email", value=email)

            home_address = "{}\n{}, {} {}".format(
                row["home street address"],
                row["home city"],
                row["home state"],
                row["home zip code"],
            )
            if "Legislative Office Building" not in home_address:
                leg.add_contact_detail(
                    type="address", value=home_address, note="District Office"
                )
                if row["home phone"].strip():
                    leg.add_contact_detail(
                        type="voice", value=row["home phone"], note="District Office"
                    )
            leg.add_source(leg_url)

            for comm_name in row["committee member1"].split(";"):
                if " (" in comm_name:
                    comm_name, role = comm_name.split(" (")
                    role = role.strip(")").lower()
                else:
                    role = "member"
                comm_name = comm_name.strip()
                if comm_name:
                    if comm_name in committees:
                        com = committees[comm_name]
                    else:
                        com = Organization(
                            comm_name, classification="committee", chamber=chamber
                        )
                        com.add_source(leg_url)
                        committees[comm_name] = com
                        yield com

                    leg.add_membership(name_or_org=com, role=role)

            yield leg
