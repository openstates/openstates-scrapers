import unicodedata
from openstates_core.scrape import Scraper, Person
from .utils import MDBMixin


class NJPersonScraper(Scraper, MDBMixin):
    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]["name"]
            self.info("no session specified, using %s", session)

        year_abr = session[0:4]

        self._init_mdb(int(year_abr))

        roster_csv = self.access_to_csv("Roster")
        bio_csv = self.access_to_csv("LegBio")

        photos = {}
        for rec in bio_csv:
            photos[rec["Roster Key"]] = rec["URLPicture"]

        for rec in roster_csv:
            first_name = rec["Firstname"]
            middle_name = rec["MidName"]
            last_name = rec["LastName"]
            suffix = rec["Suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace("  ", " ")
            full_name = full_name[0 : len(full_name) - 1]

            district = str(int(rec["District"]))
            party = rec["Party"]
            if party == "R":
                party = "Republican"
            elif party == "D":
                party = "Democratic"
            else:
                party = party
            chamber = rec["House"]
            if chamber == "A":
                chamber = "lower"
            elif chamber == "S":
                chamber = "upper"

            leg_status = rec["LegStatus"]
            # skip Deceased/Retired members
            if leg_status != "Active":
                continue
            phone = rec["Phone"] or None
            email = None
            if rec["Email"]:
                email = rec["Email"]

            # Email has been removed from the Access DB, but it's
            # still AsmLAST@njleg.org and SenLAST@njleg.org - many
            # reps have these emails on their personal pages even if
            # they're gone from the DB file
            if not email:
                email = self._construct_email(chamber, rec["Sex"], last_name)

            try:
                photo_url = photos[rec["Roster Key"]]
            except KeyError:
                photo_url = ""
                self.warning("no photo url for %s", rec["Roster Key"])
            url = "http://www.njleg.state.nj.us/members/bio.asp?Leg=" + str(
                int(rec["Roster Key"])
            )
            address = "{0}\n{1}, {2} {3}".format(
                rec["Address"], rec["City"], rec["State"], rec["Zipcode"]
            )
            gender = {"M": "Male", "F": "Female"}[rec["Sex"]]

            person = Person(
                name=full_name,
                district=district,
                primary_org=chamber,
                party=party,
                image=photo_url,
                gender=gender,
            )

            person.add_link(url)
            person.add_source(url)
            person.add_source("http://www.njleg.state.nj.us/downloads.asp")

            person.add_contact_detail(
                type="address", value=address, note="District Office"
            )
            if phone is not None:
                person.add_contact_detail(
                    type="voice", value=phone, note="District Office"
                )
            if email is not None:
                person.add_contact_detail(
                    type="email", value=email, note="District Office"
                )

            yield person

    def _construct_email(self, chamber, sex, last_name):
        # translate accents to non-accented versions for use in an
        # email and drop apostrophes and hyphens
        last_name = "".join(
            c
            for c in unicodedata.normalize("NFD", str(last_name))
            if unicodedata.category(c) != "Mn"
        )
        last_name = last_name.replace("'", "").replace("-", "").replace(" ", "")
        sex_noun = {"M": "m", "F": "w"}[sex]

        if chamber == "lower":
            return "As{}{}@njleg.org".format(sex_noun, last_name)
        else:
            return "Sen" + last_name + "@njleg.org"
