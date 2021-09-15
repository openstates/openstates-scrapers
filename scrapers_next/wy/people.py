from spatula import URL, JsonListPage, JsonPage
from openstates.models import ScrapePerson


class LegDetail(JsonPage):
    def process_page(self):
        p = self.input

        img = f"https://wyoleg.gov/LegislatorSummary/Photos/{self.data['legPhoto']}"
        p.image = img

        # self.data['county']
        # self.data['remarks']
        # self.data['occupationDesc']
        # self.data['civicOrgs']
        # self.data['legEducation']
        # self.data['legLeadership']
        # self.data['cityList']
        # self.data['countyList']
        # self.data['legPriorService']
        # self.data['districtList']
        # self.data['officesHeld']
        # self.data['spouseName']
        # self.data['noChildren']
        # self.data['noGChildren']
        # self.data['occupWeb']
        # self.data['dob']
        # self.data['birthPlace']
        # self.data['religion']
        # self.data['firstYrHouse']
        # self.data['lastYrHouse']
        # self.data['firstYrSenate']
        # self.data['lastYrSenate']
        # self.data['houseYears']
        # self.data['senateYears']

        # self.data['address']
        # self.data['city']
        # self.data['state']
        # self.data['zip']
        # self.data['onWeb']
        # self.data['areaCode']
        # self.data['phoneType']
        # self.data['leadershipPosition']
        # self.data['leadershipOrder']
        # self.data['currentLeadershipPosition']
        # self.data['legStatus']

        return p


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

        # assuming this is a district office phone
        p.district_office.voice = item["phone"].strip()

        detail_link = f"https://wyoleg.gov/LsoService/api/legislator/{item['legID']}"
        p.add_source(detail_link)
        # should I add detail_link as homepage?

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/S")
    chamber = "upper"


class House(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/H")
    chamber = "lower"
