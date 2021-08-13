from spatula import CsvListPage
from openstates.models import ScrapePerson


class LegList(CsvListPage):
    source = "ftp://ftp.cga.ct.gov/pub/data/LegislatorDatabase.csv"

    def process_item(self, row):
        name = row["first name"]
        mid = row["middle initial"].strip()
        if mid:
            name += " %s" % mid
        name += " %s" % row["last name"]
        suffix = row["suffix"].strip()
        if suffix:
            name += " %s" % suffix

        party = row["party"]

        district = row["dist"].lstrip("0")
        assert district.isdigit(), "Invalid district found: {}".format(district)

        chamber = {"H": "lower", "S": "upper"}[row["office code"]]

        email = row["email"].strip()
        if "@" not in email:
            if not email:
                email = ""
            elif email.startswith("http://") or email.startswith("https://"):
                email = ""
            else:
                raise ValueError("Problematic email found: {}".format(email))

        p = ScrapePerson(
            name=name,
            state="ct",
            chamber=chamber,
            district=district,
            party=party,
            email=email,
        )

        legislator_url = row["URL"].replace("\\", "//").strip()
        if legislator_url != "":
            if not legislator_url.startswith("http"):
                legislator_url = "http://"
        p.add_link(legislator_url)

        p.add_source(self.source.url)

        # the spacing of the address?
        office_address = "%s Room %s; %s" % (
            row["capitol street address"],
            row["room number"],
            row["capitol city"].replace("  ", " "),
        )
        p.capitol_office.address = office_address

        if row["capitol phone"].strip():
            p.capitol_office.voice = row["capitol phone"]

        # spacing?
        if row["home street address"] and row["home city"]:
            home_address = "{}; {}, {} {}".format(
                row["home street address"],
                row["home city"],
                row["home state"],
                row["home zip code"],
            )

            if "Legislative Office Building" not in home_address:
                p.district_office.address = home_address

        types = [
            "gender",
            "title",
            "committee member1",
            "committee codes",
            "business phone",
            "fax",
            "prison",
        ]

        for type in types:
            if row[type] != " ":
                if type == "committee member1":
                    type_changed = "committees"
                    p.extras[type_changed] = row[type]
                else:
                    p.extras[type] = row[type]
        return p
