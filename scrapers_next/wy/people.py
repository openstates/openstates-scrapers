from spatula import URL, JsonListPage
from openstates.models import ScrapePerson


class LegList(JsonListPage):
    def process_item(self, item):
        name = item["name"].strip()

        party = item["party"].strip()
        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"
        elif party == "I":
            party = "Independent"
        elif party == "L":
            party = "Libertarian"

        district = item["district"].strip().lstrip("SH0")

        p = ScrapePerson(
            name=name,
            state="wy",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        p.add_source(self.source.url)

        p.given_name = item["firstName"].strip()
        p.family_name = item["lastName"].strip()

        p.email = item["eMail"].strip()

        # item['leadershipOrder']
        # item['legStatus']
        # item['county']
        # item['legID']

        # assuming this is a district office phone
        p.district_office.voice = item["phone"].strip()

        return p


class Senate(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/S")
    chamber = "upper"


class House(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/H")
    chamber = "lower"
