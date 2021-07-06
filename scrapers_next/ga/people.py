from spatula import JsonListPage
from openstates.models import ScrapePerson


class DirectoryListing(JsonListPage):
    # e.g. https://www.legis.ga.gov/api/members/list/1029?chamber=1
    # these pages are seen as XHR when loading https://www.legis.ga.gov/members/senate
    chamber_types = {1: "lower", 2: "upper"}
    chamber_names = {1: "house", 2: "senate"}
    party_ids = {0: "Democratic", 1: "Republican"}

    def process_item(self, item):
        chamber_id = item["district"]["chamberType"]
        p = ScrapePerson(
            state="ga",
            chamber=self.chamber_types[chamber_id],
            district=str(item["district"]["number"]),
            name=item["fullName"],
            family_name=item["name"]["familyName"],
            given_name=item["name"]["first"],
            suffix=item["name"]["suffix"] or "",
            party=self.party_ids[item["party"]],
        )

        # district address
        da = item["districtAddress"]
        p.email = da["email"]
        p.district_office.voice = da["phone"]
        p.district_office.fax = da["fax"]
        if da["address1"]:
            p.district_office.address = da["address1"]
            if da["address2"]:
                p.district_office.address += "; " + da["address2"]
            p.district_office.address += "; {city}, {state} {zip}".format(**da)
            p.district_office.address = p.district_office.address.strip()

        # photos
        if not item["photos"]:
            pass
        elif len(item["photos"]) == 1:
            p.image = item["photos"][0]["url"].split("?")[
                0
            ]  # strip off ?size=mpSm for full size
        else:
            raise Exception("unknown photos configuration: " + str(item["photos"]))

        # extras
        p.extras["residence"] = item["residence"]
        p.extras["city"] = item["city"]
        p.extras["georgia_id"] = item["id"]
        if item["dateVacated"]:
            p.end_date = item["dateVacated"]

        url = (
            f"https://www.legis.ga.gov/members/{self.chamber_names[chamber_id]}/"
            f"{item['id']}?session={item['sessionId']}"
        )
        p.add_source(url)
        p.add_link(url)

        return p


people = DirectoryListing(source="https://www.legis.ga.gov/api/members/list/1029")
