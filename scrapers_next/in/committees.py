from spatula import URL, HtmlListPage, SkipItem, HtmlPage
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        if com:
            for each_member in self.response.json()["members"]:
                role = str(each_member["position"])
                role = (
                    role.lower()
                    .replace("majority ", "")
                    .replace("minority ", "")
                    .title()
                )
                name = f'{each_member["first_name"]} {each_member["last_name"]}'
                com.add_member(name, role)

            com.add_source(
                self.source.url,
                note="Committee Details API",
            )
        return com


class CommitteeList(HtmlListPage):
    session_year = 2025
    source = URL(
        f"https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getCommittees?session_lpid=session_{session_year}",
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

    def process_page(self, only_name=False):
        all_committees = self.response.json()["committees"]
        for committee in all_committees:
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
                # getting parent committee name from committees
                for cm in all_committees:
                    if cm["id"] == committee["parent_committee_id"]:
                        parent = cm["name"]
            else:
                parent = None
                classification = "committee"

            try:
                mem_source = f"https://tlhgp53g3c.execute-api.us-east-2.amazonaws.com/beta/api/getMembers?committee_id={committee['id']}&session_lpid=session_{self.session_year}"
            except KeyError:
                raise SkipItem(f"Name: {name} skipped due to invalid key committee id")
            if committee:
                com = ScrapeCommittee(
                    name=name,
                    chamber=chamber,
                    parent=parent,
                    classification=classification,
                )

                com.add_source(
                    self.source.url,
                    note="Committee List API from current beta version of Indiana gov site",
                )

                # TODO: update with better HTML link once Indiana has launched
                #   their new legislative site. Currently, the "homepage" link
                #   for each comm will point to list of all standing committees
                coms_link = "https://iga.in.gov/2025/committees/"
                com.add_link(coms_link, note="homepage")

                yield CommitteeDetail(
                    com, source=URL(mem_source, timeout=30, headers=self.source.headers)
                )
