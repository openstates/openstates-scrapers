from spatula import URL, HtmlListPage, HtmlPage, CSS, XPath, selectors
from openstates.models import ScrapeCommittee
import requests

requests.packages.urllib3.disable_warnings()


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        com.add_source(
            self.source.url,
            note="Committee Details Page",
        )
        try:
            member_blocks = XPath('//*[contains(@class, "committeeMemberList")]').match(
                self.root
            )[0]
        except selectors.SelectorError:
            return com
        for data in member_blocks:
            # break if no members is in the list
            if "There are no members" in data.text:
                break
            # continue to extract members if available
            name = None
            role = "Member"
            for info in data.text_content().splitlines():
                if not info.strip():
                    continue
                if not name:
                    name = info.strip().title()
                else:
                    role = info.strip().replace(")", "").replace("(", "").title()
            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL(
        "https://malegislature.gov/Committees",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
        },
        verify=False,
    )

    def process_page(self):
        for committees in XPath('//*[contains(@class, "committeeList")]').match(
            self.root
        ):
            for each_committee in committees:
                name = str(each_committee.text_content())
                if any(name.startswith(s) for s in ["House", "Senate", "Joint"]):
                    cm_url = CSS("a").match_one(each_committee).get("href")
                    if "house committee" in name.lower():
                        chamber = "lower"
                    elif "senate committee" in name.lower():
                        chamber = "upper"
                    else:
                        chamber = "legislature"
                    classification = "committee"
                    parent = None

                    com = ScrapeCommittee(
                        name=name,
                        chamber=chamber,
                        parent=parent,
                        classification=classification,
                    )

                    com.add_source(
                        cm_url,
                        note="Committee List page of malegislature gov site",
                    )

                    yield CommitteeDetail(
                        com,
                        source=URL(
                            cm_url,
                            timeout=30,
                            headers=self.source.headers,
                            verify=False,
                        ),
                    )
