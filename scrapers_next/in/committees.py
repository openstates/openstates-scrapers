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
        "https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getCommittees?session_lpid=session_2021",
        headers={
            "authority": "beta.iga.in.gov",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="108", "Opera";v="94", "Not)A;Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 OPR/94.0.0.0",
        },
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
                yield CommitteeDetail(
                    com, source=URL(mem_source, timeout=30, headers=self.source.headers)
                )
