import json
import datetime

from openstates_core.scrape import Scraper, Person


class WYPersonScraper(Scraper):
    party_map = {"R": "Republican", "D": "Democratic", "I": "Independent"}

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_abbrev = {"upper": "S", "lower": "H"}[chamber]

        url = "https://wyoleg.gov/LsoService/api/legislator/{}/{}".format(
            session, chamber_abbrev
        )

        response = self.get(url)
        people_json = json.loads(response.content.decode("utf-8"))

        for row in people_json:

            # some fields are only available in the list json, some only in the details call
            details_url = "https://wyoleg.gov/LsoService/api/legislator/{}".format(
                row["legID"]
            )
            details_response = self.get(details_url)
            details = json.loads(details_response.content.decode("utf-8"))

            party = self.party_map[row["party"]]

            if details["dob"] is not None:
                dob = datetime.datetime.strptime(details["dob"], "%m/%d/%Y %I:%M:%S %p")
                dob_str = datetime.datetime.strftime(dob, "%Y-%m-%d")
            else:
                dob_str = ""

            photo_url = "http://wyoleg.gov/LegislatorSummary/Photos/{}".format(
                details["legPhoto"]
            )

            person = Person(
                name=row["name"],
                district=row["district"].lstrip("SH0"),
                party=party,
                primary_org=chamber,
                birth_date=dob_str,
                image=photo_url,
            )

            if details["address"]:
                address = "{}, {} {} {}".format(
                    details["address"],
                    details["city"],
                    details["state"],
                    details["zip"],
                )
                person.add_contact_detail(type="address", value=address)

            if row["eMail"]:
                person.add_contact_detail(type="email", value=row["eMail"])

            if row["phone"]:
                person.add_contact_detail(type="voice", value=row["phone"])

            person.extras["wy_leg_id"] = row["legID"]
            person.extras["county"] = row["county"]
            person.extras["given_name"] = row["firstName"]
            person.extras["family_name"] = row["lastName"]
            person.extras["religion"] = details["religion"]
            person.extras["number_children"] = details["noChildren"]
            person.extras["spouse_given_name"] = details["spouseName"]
            person.extras["place_of_birth"] = details["birthPlace"]
            person.extras["occupation"] = details["occupationDesc"]

            if details["legEducation"]:
                person.extras["education"] = details["legEducation"]

            if details["civicOrgs"]:
                person.extras["civic_organizations"] = details["civicOrgs"]

            # http://wyoleg.gov/Legislators/2018/S/2032
            leg_url = "http://wyoleg.gov/Legislators/{}/{}/{}".format(
                session, row["party"], row["legID"]
            )

            person.add_source(leg_url)
            person.add_link(leg_url)

            yield person
