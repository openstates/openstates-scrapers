from spatula import URL, JsonListPage, JsonPage
from openstates.models import ScrapeCommittee
from .utils import get_token


class CommitteeDetail(JsonPage):
    def process_page(self):
        com = self.input
        com.add_source(
            self.source.url, note="Detail page (requires authorization token)"
        )

        if com.chamber == "upper":
            link_chamber = "senate"
        elif com.chamber == "lower":
            link_chamber = "house"

        source_url_list = self.source.url.split("/")
        item_id = source_url_list[-2]

        link = f"https://www.legis.ga.gov/committees/{link_chamber}/{item_id}"
        com.add_link(link, note="homepage")

        com_address = self.data["address"]["address1"].strip() + " "
        com_address += self.data["address"]["address2"].strip() + " "
        com_address += self.data["address"]["city"].strip()
        com_address += ", "
        com_address += self.data["address"]["state"].strip() + " "
        com_address += self.data["address"]["zip"].strip()

        com_phone = self.data["address"]["phone"].strip()
        com_fax = self.data["address"]["fax"].strip()
        com_email = self.data["address"]["email"]

        if com_address:
            com.extras["address"] = com_address
        if com_phone:
            com.extras["phone"] = com_phone
        if com_fax:
            com.extras["fax"] = com_fax
        if com_email:
            com.extras["email"] = com_email

        for memb in self.data["members"]:
            member = memb["name"]
            role = memb["role"]
            com.add_member(member, role)

        return com


class CommitteeList(JsonListPage):

    source = URL(
        "https://www.legis.ga.gov/api/committees/List/1029",
        headers={"Authorization": get_token()},
    )

    def process_item(self, item):
        if item["chamber"] == 2:
            chamber = "upper"
        elif item["chamber"] == 1:
            chamber = "lower"

        source = URL(
            f"https://www.legis.ga.gov/api/committees/details/{item['id']}/1029",
            headers={"Authorization": get_token()},
        )

        com = ScrapeCommittee(
            name=item["name"],
            chamber=chamber,
        )

        com.add_source(
            self.source.url, note="Initial list page (requires authorization token)"
        )

        return CommitteeDetail(
            com,
            source=source,
        )
