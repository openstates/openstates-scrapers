from spatula import JsonListPage
from openstates.models import ScrapePerson


class LegList(JsonListPage):
    def process_item(self, item):
        print(item["Data"])
        for item in self.data["Data"]:
            name = item["PersonFullName"]
            party_code = item["PartyCode"]
            party_dict = {"D": "Democratic", "R": "Republican", "I": "Independent"}
            party = party_dict[party_code]
            district = item["DistrictNumber"]

            p = ScrapePerson(
                name=name,
                state="de",
                party=party,
                chamber=self.chamber,
                district=district,
            )

            return p


class Senate(LegList):
    source = "https://legis.delaware.gov/json/Senate/GetSenators"
    chamber = "upper"


class House(LegList):
    source = "https://legis.delaware.gov/json/House/GetRepresentatives"
    chamber = "lower"
