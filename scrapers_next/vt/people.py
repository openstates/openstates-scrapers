from spatula import URL, JsonPage
from openstates.models import ScrapePerson
import re


class LegList(JsonPage):
    source = URL("https://legislature.vermont.gov/people/loadAll/2022")

    def process_page(self):
        legislators = self.data["data"]

        for leg in legislators:
            if leg["MI"].strip() != "":
                name = (
                    leg["FirstName"].strip()
                    + " "
                    + leg["MI"].strip()
                    + ". "
                    + leg["LastName"].strip()
                )
            else:
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
            p.add_source(self.source.url)

            p.given_name = leg["FirstName"].strip()
            p.family_name = leg["LastName"].strip()
            if leg["NameSuffix"].strip() != "":
                p.suffix = leg["NameSuffix"].strip()
            if leg["Email"].strip() != "":
                p.email = leg["Email"].strip()

            work_addr = ""
            if leg["WorkAddress1"].strip() != "":
                work_addr += leg["WorkAddress1"].strip()
                work_addr += " "
            if leg["WorkAddress2"].strip() != "":
                work_addr += leg["WorkAddress2"].strip()
                work_addr += " "
            if leg["WorkCity"].strip() != "":
                work_addr += leg["WorkCity"].strip()
                work_addr += ", "
            if leg["WorkState"].strip() != "":
                work_addr += leg["WorkState"].strip()
                work_addr += " "
            if leg["WorkZIP"].strip() != "":
                work_addr += leg["WorkZIP"].rstrip("-").strip()
                work_addr += " "
            if work_addr.strip() != "":
                p.extras["work address"] = work_addr.strip()

            if (
                leg["WorkEmail"].strip() != ""
                and leg["WorkEmail"].strip() != leg["Email"].strip()
            ):
                p.extras["work email"] = leg["WorkEmail"].strip()

            home_addr = ""
            if leg["HomeAddress1"].strip() != "":
                home_addr += leg["HomeAddress1"].strip()
                home_addr += " "
            if leg["HomeAddress2"].strip() != "":
                home_addr += leg["HomeAddress2"].strip()
                home_addr += " "
            if leg["HomeCity"].strip() != "":
                home_addr += leg["HomeCity"].strip()
                home_addr += ", "
            if leg["HomeState"].strip() != "":
                home_addr += leg["HomeState"].strip()
                home_addr += " "
            if leg["HomeZIP"].strip() != "":
                home_addr += leg["HomeZIP"].rstrip("-").strip()
                home_addr += " "
            if home_addr.strip() != "":
                p.extras["home address"] = home_addr.strip()

            if leg["HomePhone"].strip() != "":
                p.extras["home phone"] = leg["HomePhone"].strip()

            if (
                leg["HomeEmail"].strip() != ""
                and leg["HomeEmail"].strip() != leg["Email"].strip()
            ):
                p.extras["home email"] = leg["HomeEmail"].strip()

            mail_addr = ""
            if leg["MailingAddress1"].strip() != "":
                mail_addr += leg["MailingAddress1"].strip()
                mail_addr += " "
            if leg["MailingAddress2"].strip() != "":
                mail_addr += leg["MailingAddress2"].strip()
                mail_addr += " "
            if leg["MailingCity"].strip() != "":
                mail_addr += leg["MailingCity"].strip()
                mail_addr += ", "
            if leg["MailingState"].strip() != "":
                mail_addr += leg["MailingState"].strip()
                mail_addr += " "
            if leg["MailingZIP"].strip() != "":
                mail_addr += leg["MailingZIP"].strip()
                mail_addr += " "
            if mail_addr.strip() != "":
                p.extras["mailing address"] = mail_addr.strip()

            yield p

            # leg['DistrictMap']
            # leg['vTown']
            # leg['PersonID']
            # leg['Town']
