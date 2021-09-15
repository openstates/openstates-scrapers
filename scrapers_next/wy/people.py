from spatula import URL, JsonListPage, JsonPage
from openstates.models import ScrapePerson


class LegDetail(JsonPage):
    def process_page(self):
        p = self.input

        img = f"https://wyoleg.gov/LegislatorSummary/Photos/{self.data['legPhoto']}"
        p.image = img

        # assuming this is a district address
        distr_addr = f"{self.data['address']}, {self.data['city']}, {self.data['state']} {self.data['zip']}"
        p.district_office.address = distr_addr

        # self.data['phoneType']

        p.extras["county"] = self.data["county"]
        if self.data["legEducation"] != []:
            p.extras["education"] = self.data["legEducation"]
        if self.data["currentLeadershipPosition"] is not None:
            p.extras["title"] = self.data["currentLeadershipPosition"].strip()
        if self.data["religion"].strip() != "":
            p.extras["religion"] = self.data["religion"].strip()
        if self.data["spouseName"] is not None:
            p.extras["spouse name"] = self.data["spouseName"]
        if self.data["noChildren"].strip() != "":
            p.extras["number of children"] = self.data["noChildren"]
        if self.data["noGChildren"].strip() != "":
            p.extras["number of grandchildren"] = self.data["noGChildren"]
        if self.data["birthPlace"].strip() != "":
            p.extras["birth place"] = self.data["birthPlace"]
        if self.data["occupationDesc"] is not None:
            p.extras["occupation"] = self.data["occupationDesc"]
        if self.data["legLeadership"] != []:
            p.extras["leadership"] = self.data["legLeadership"]
        if self.data["civicOrgs"] != []:
            p.extras["organizations"] = self.data["civicOrgs"]
        if self.data["houseYears"].strip() != "":
            p.extras["house years"] = self.data["houseYears"]
        if self.data["senateYears"].strip() != "":
            p.extras["senate years"] = self.data["senateYears"]
        p.extras["prior service"] = self.data["legPriorService"]

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

        # assuming this is a district office phone
        p.district_office.voice = item["phone"].strip()

        detail_link = f"https://wyoleg.gov/LsoService/api/legislator/{item['legID']}"
        p.add_source(detail_link)
        # should I add detail_link as homepage?

        leg_url = f"http://wyoleg.gov/Legislators/2021/{item['party']}/{item['legID']}"
        p.add_link(leg_url, note="homepage")

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/S")
    chamber = "upper"


class House(LegList):
    source = URL("https://wyoleg.gov/LsoService/api/legislator/2021/H")
    chamber = "lower"
