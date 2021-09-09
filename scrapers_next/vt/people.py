from spatula import URL, JsonPage
from openstates.models import ScrapePerson
import re


class LegList(JsonPage):
    source = URL("https://legislature.vermont.gov/people/loadAll/2022")

    def process_page(self):
        legislators = self.data["data"]

        for leg in legislators:
            name = leg["FirstName"].strip() + " " + leg["LastName"].strip()

            party = leg["Party"].strip()
            party = re.sub("Democrat", "Democratic", party)

            district = leg["District"].strip()

            if leg["Title"].strip() == "Senator":
                chamber = "upper"
            elif leg["Title"].strip() == "Representative":
                chamber = "lower"

            p = ScrapePerson(
                name=name, state="vt", chamber=chamber, district=district, party=party
            )
            p.given_name = leg["FirstName"].strip()
            p.family_name = leg["LastName"].strip()

            yield p

            # leg['HomeAddress2']
            # leg['HomeAddress1']
            # leg['HomeEmail']
            # leg['MI']
            # leg['NameSuffix']
            # leg['Email']
            # leg['WorkAddress2']
            # leg['Town']
            # leg['MailingAddress2']
            # leg['MailingAddress1']
            # leg['HomeZIP']
            # leg['DistrictMap']
            # leg['WorkState']
            # leg['vTown']
            # leg['MailingCity']
            # leg['HomeCity']
            # leg['MailingZIP']
            # leg['WorkCity']
            # leg['WorkEmail']
            # leg['MailingState']
            # leg['WorkZIP']
            # leg['WorkAddress1']
            # leg['TerminationReason']
            # leg['HomePhone']
            # leg['HomeState']
            # leg['PersonTypeID']
            # leg['PersonID']
