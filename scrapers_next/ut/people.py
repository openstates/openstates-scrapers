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

            p = ScrapePerson(
                name=name, state="ut", chamber=chamber, district=district, party=party
            )

            p.add_source(self.source.url)

            p.image = leg["image"]

            try:
                p.email = leg["email"].strip()
            except KeyError:
                self.logger.warning(f"No email for {name}")

            if leg["address"].strip() != ", , ,":
                if (
                    "state st" in leg["address"].strip().lower()
                    and "salt lake city" in leg["address"].strip().lower()
                ):
                    p.capitol_office.address = leg["address"].strip()
                else:
                    p.district_office.address = leg["address"].strip()

            # Note about phones from old code
            # Work phone seems to be the person's non-legislative
            # office phone, and thus a last option
            # For example, we called one and got the firm
            # where he's a lawyer. We're picking
            # them in order of how likely we think they are
            # to actually get us to the person we care about.
            if leg.get("workPhone", None):
                p.capitol_office.voice = leg["workPhone"]
            elif "cell" in leg:
                if leg["cell"][:3] == "801" or leg["cell"][:3] == "385":
                    p.capitol_office.voice = leg["cell"]
                else:
                    p.district_office.voice = leg["cell"]
            # this seems like it wouldn't be right, but there are reps that have this number listed as
            # their official number
            elif "homePhone" in leg:
                if leg["homePhone"][:3] == "801" or leg["homePhone"][:3] == "385":
                    p.capitol_office.voice = leg["homePhone"]
                else:
                    p.district_office.voice = leg["homePhone"]

            p.add_link(leg["legislation"], note="legislation")

            if leg["serviceStart"].strip() != "":
                p.extras["service start"] = leg["serviceStart"].strip()

            if leg["profession"].strip() != "":
                p.extras["profession"] = leg["profession"].strip()

            if leg["education"].strip() != "":
                p.extras["education"] = leg["education"].strip()

            p.extras["counties represented"] = []
            for county in leg["counties"].split(","):
                p.extras["counties represented"] += [county.strip()]

            p.add_link(leg["demographic"], note="district demographics")

            if leg.get("CofI", None):
                for num, url in enumerate(leg["CofI"]):
                    p.add_link(url["url"], note=f"conflict of interest {num}")

            if (
                leg["FinanceReport"][0]["url"]
                != "http://www.disclosures.utah.gov/Search/PublicSearch"
            ):
                p.add_link(leg["FinanceReport"][0]["url"], note="finance report")

            if chamber == "upper":
                detail_link = f"https://senate.utah.gov/sen/{leg['id']}/"
            elif chamber == "lower":
                detail_link = f"http://house.utah.gov/rep/{leg['id']}/"
            p.add_source(detail_link)
            p.add_link(detail_link, note="homepage")

            if leg.get("cell", None):
                p.extras["cell phone"] = leg["cell"].strip()

            if leg.get("fax", None):
                p.district_office.fax = leg["fax"].strip()

            if leg.get("homePhone", None):
                p.extras["home phone"] = leg["homePhone"].strip()

            if leg.get("position", None):
                p.extras["title"] = leg["position"].strip()

            yield p
