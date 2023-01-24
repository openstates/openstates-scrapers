from spatula import URL, HtmlListPage, SkipItem

from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlListPage):
    source = URL(
        "https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getMembers?committee_id=840b8a47-2a40-4e28-9e2a-68e6c66c9e45&session_lpid=session_2021"
    )

    def process_page(self):
        com = self.input
        if com:
            for each_member in self.response.json()["members"]:
                role = each_member["position_lpid"]
                name = each_member["first_name"] + " " + each_member["last_name"]
                com.add_member(name, role)

            com.add_source(self.source.url)
            com.extras["members"] = self.response.json()["members"]
            return com


class CommitteeList(HtmlListPage):
    source = URL(
        "https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getCommittees?session_lpid=session_2021"
    )

    def process_page(self):
        for committee in self.response.json()["committees"]:
            name = committee["name"]

            chamber = committee["chamber_lpid"]
            if chamber == "senate":
                chamber = "upper"
            elif chamber == "house":
                chamber = "lower"
            else:
                chamber = "legislature"

            if "subcommittee" in name.lower():
                classification = "subcommittee"
                parent = name
            else:
                parent = None
                classification = "committee"
            try:
                mem_source = f"https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getMembers?committee_id={committee['id']}&session_lpid=session_2021"
            except KeyError:
                raise SkipItem(committee)
            if committee:
                com = ScrapeCommittee(
                    name=name,
                    chamber=chamber,
                    parent=parent,
                    classification=classification,
                )

                com.add_source(
                    self.source.url,
                    note="API from https://beta.iga.in.gov/2022/committees/",
                )
                com.extras = {"committees": committee}
                yield CommitteeDetail(com, source=URL(mem_source, timeout=30))
