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

        # item['city']
        # item['state']
        # item['zip']

        # assuming this is a district office phone
        p.district_office.voice = item["phone"].strip()

        # item['religion']
        # item['onWeb']
        # item['districtList']
        # item['lastYrSenate']
        # item['officesHeld']
        # item['noGChildren']
        # item['legStatus']
        # item['legID']
        # item['occupationDesc']
        # item['legEducation']
        # item['houseYears']
        # item['currentLeadershipPosition']
        # item['dob']
        # item['spouseName']
        # item['legPriorService']
        # item['county']
        # item['birthPlace']
        # item['occupWeb']
        # item['leadershipPosition']
        # item['lastYrHouse']
        # item['legSponsorYears']
        # item['countyList']
        # item['senateYears']
        # item['remarks']
        # item['noChildren']
        # item['firstYrHouse']
        # item['legCommYears']
        # item['cityList']
        # item['firstYrSenate']
        # item['leadershipOrder']
        # item['civicOrgs']
        # item['legLeadership']

        return p


class Senate(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/S")
    chamber = "upper"


class House(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/H")
    chamber = "lower"
