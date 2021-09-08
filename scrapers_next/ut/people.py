from spatula import URL, JsonPage
from openstates.models import ScrapePerson


class LegList(JsonPage):
    source = URL("https://le.utah.gov/data/legislators.json")

    def process_page(self):
        legislators = self.data["legislators"]
        for leg in legislators:
            name = leg["formatName"]

            if leg["house"].strip() == "H":
                chamber = "lower"
            else:
                chamber = "upper"

            if leg["party"].strip() == "D":
                party = "Democratic"
            elif leg["party"].strip() == "R":
                party = "Republican"

            district = leg["district"].strip()

            # leg['id']
            # leg['image']
            # leg['serviceStart']
            # leg['profession']
            # leg['professionalAffiliations']
            # leg['education']
            # leg['recognitionsAndHonors']
            # leg['counties']
            # leg['address']
            # leg['email']
            # leg['workPhone']
            # leg['committees']
            # leg['legislation']
            # leg['demographic']
            # leg['CofI']
            # leg['FinanceReport']

            p = ScrapePerson(
                name=name, state="ut", chamber=chamber, district=district, party=party
            )

            yield p
