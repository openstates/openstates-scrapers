from spatula import URL, HtmlListPage, HtmlPage, CSS, XPath, selectors
from openstates.models import ScrapeCommittee
import requests

requests.packages.urllib3.disable_warnings()


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        try:
            for members_area in XPath(
                '//*[contains(@class, "committeeMemberList")]'
            ).match_one(self.root)[0]:
                if "There are no members" in members_area.text:
                    break
                # continue to extract members if available
                for members_info in XPath(
                    '//*[contains(@class, "committeeMemberList")]'
                ).match_one(members_area):
                    for data in members_info:
                        name = None
                        role = "Member"
                        for info in data.text_content().splitlines():
                            if info.strip():
                                if name is None:
                                    name = info.strip()
                                else:
                                    role = info.strip()
                        com.add_member(name, role)
        except selectors.SelectorError:
            return com
        com.add_source(
            self.source.url,
            note="Committee Details Page",
        )
        return com


class CommitteeList(HtmlListPage):
    source = URL(
        "https://malegislature.gov/Committees",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        },
        verify=False,
    )

    def process_page(self):
        for comm in XPath('//*[contains(@class, "committeeList")]').match(self.root):
            for each_committee in comm:
                if comm is not None:
                    name = str(each_committee.text_content())
                    if (
                        name.startswith("House")
                        or name.startswith("Senate")
                        or name.startswith("Joint")
                    ):
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
