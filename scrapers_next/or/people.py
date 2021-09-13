from spatula import URL, XmlPage
from openstates.models import ScrapePerson

# from .apiclient import OregonLegislatorODataClient
# from .utils import SESSION_KEYS


class LegList(XmlPage):
    source = URL(
        "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions('2021R1')/Legislators"
    )

    def process_page(self):
        for leg in self.root[4:]:
            content = leg[9]

            first_name = content[0][2].text
            last_name = content[0][3].text
            name = first_name.strip() + " " + last_name.strip()

            chamber = content[0][7].text
            if chamber.strip() == "H":
                chamber = "lower"
            elif chamber.strip() == "S":
                chamber = "upper"

            party = content[0][8].text
            if party.strip() == "Democrat":
                party = "Democratic"

            district = content[0][9].text

            p = ScrapePerson(
                name=name,
                state="or",
                chamber=chamber,
                district=district,
                party=party,
            )
            # session_key = content[0][0].text
            # legislator_code = content[0][1].text
            # cap_address = content[0][4].text
            # cap_phone = content[0][5].text
            # title = content[0][6].text
            # email = content[0][10].text
            # website = content[0][11].text
            # created_date = content[0][12].text
            # modified_date = content[0][13].text

            yield p
