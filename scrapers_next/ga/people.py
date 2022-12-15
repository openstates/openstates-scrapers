import re
from spatula import JsonListPage, JsonPage, URL
from openstates.models import ScrapePerson
from .utils import get_token


class LegDetail(JsonPage):
    def process_page(self):
        p = self.input
        p.add_source(self.source.url, note="Detail page (requires authorization token)")
        if self.data["email"]:
            p.email = self.data["email"]

        try:
            capitol_office = (
                self.data["capitolAddress"]["address1"]
                + "; "
                + self.data["capitolAddress"]["city"]
                + ", GA "
                + self.data["capitolAddress"]["zip"].strip()
            )
            p.capitol_office.address = capitol_office
            p.capitol_office.voice = self.data["capitolAddress"]["phone"]

            if self.data["capitolAddress"]["fax"]:
                p.capitol_office.fax = self.data["capitolAddress"]["fax"]
        except TypeError:
            self.logger.warning(f"Empty capitol address for {p.name}")
            pass

        extras = [
            "birthday",
            "occupation",
            "press",
            "religion",
            "spouse",
            "staff",
            "title",
        ]

        for type_info in extras:
            info = self.data[type_info]
            if info:
                if type_info == "staff":
                    info = re.split("mailto:|>|<", info)
                    if len(info) > 1:
                        p.extras["staff"] = info[3]
                        p.extras["staff email"] = info[2].replace('"', "")
                    else:
                        p.extras["staff"] = info[0]
                        p.extras["staff email"] = ""
                else:
                    p.extras[type_info] = info

        return p


class DirectoryListing(JsonListPage):
    # e.g. https://www.legis.ga.gov/api/members/list/1029?chamber=1
    # these pages are seen as XHR when loading https://www.legis.ga.gov/members/senate
    chamber_types = {1: "lower", 2: "upper"}
    chamber_names = {1: "house", 2: "senate"}
    party_ids = {0: "Democratic", 1: "Republican"}
    source = URL(
        "https://www.legis.ga.gov/api/members/list/1029",
        headers={"Authorization": get_token()},
    )

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
        if da["email"]:
            p.email = da["email"]
        else:
            p.email = "missing@invalid.no"

        if da["phone"]:
            p.district_office.voice = da["phone"]
        if da["fax"]:
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
        p.extras["city"] = item["city"].strip()
        p.extras["georgia_id"] = item["id"]

        url = (
            f"https://www.legis.ga.gov/members/{self.chamber_names[chamber_id]}/"
            f"{item['id']}?session={item['sessionId']}"
        )
        p.add_source(url, note="Initial list page (requires authorization token)")

        source = URL(
            f"https://www.legis.ga.gov/api/members/detail/{item['id']}?session=1029&chamber={chamber_id}",
            headers={"Authorization": get_token()},
            timeout=30,
        )

        return LegDetail(p, source=source)
