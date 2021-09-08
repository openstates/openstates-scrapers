from spatula import JsonListPage, JsonPage, URL
from openstates.models import ScrapePerson
from .utils import get_token


class PeopleDetail(JsonPage):
    def process_page(self):
        p = self.input
        p.add_source(self.source.url, note="Detail page (requires authorization token)")

        p.email = self.data["email"]

        # capitol office
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
            pass
        # a lot of extras: birthday, committee memberships, occupation, press, religion, residence, sessionsinservice, spouse, staff with email, title,
        # p.extras["title"]

        # residence, city, georgia id
        extras = [
            "birthday",
            "occupation",
            "press",
            "religion",
            "spouse",
            "staff",
            "title",
        ]
        # extras = [self.data["birthday"], self.data["occupation"],self.data["press"],self.data["religion"],self.data["spouse"], self.data["staff"], self.data["title"],]
        # for info in extras:
        #     if info != 'null':
        #         p.extras[]

        # for self.data[info] in extras:
        #     print("hi", info)

        for type_info in extras:
            info = self.data[type_info]
            if info != "null":
                # p.extras[type_info] = info
                if type_info == "staff":
                    p.extras["staff"] = info
                    # p.extras["staff email"]
                else:
                    p.extras[type_info] = info

        return p


class DirectoryListing(JsonListPage):
    # e.g. https://www.legis.ga.gov/api/members/list/1029?chamber=1
    # these pages are seen as XHR when loading https://www.legis.ga.gov/members/senate
    chamber_types = {1: "lower", 2: "upper"}
    chamber_names = {1: "house", 2: "senate"}
    party_ids = {0: "Democratic", 1: "Republican"}

    # TODO: replace with utils in committees.py

    def process_item(self, item):
        chamber_id = item["district"]["chamberType"]
        print("NAME", item["fullName"])

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
        if item["dateVacated"]:
            p.end_date = item["dateVacated"]

        url = (
            f"https://www.legis.ga.gov/members/{self.chamber_names[chamber_id]}/"
            f"{item['id']}?session={item['sessionId']}"
        )
        p.add_source(url)
        # TODO: get rid of below link?
        # p.add_link(url)

        # return p

        # source may instead be including &chamber=2 at the end
        source = URL(
            f"https://www.legis.ga.gov/api/members/detail/{item['id']}?session=1029&chamber={chamber_id}",
            headers={"Authorization": get_token()},
        )

        # https://www.legis.ga.gov/api/members/detail/754?session=1029&chamber=2

        return PeopleDetail(p, source=source)


people = DirectoryListing(
    source=URL(
        "https://www.legis.ga.gov/api/members/list/1029?",
        headers={"Authorization": get_token()},
    )
)
#     source = URL(
#     "https://www.legis.ga.gov/api/committees/List/1029",
#     headers={"Authorization": get_token()},)
