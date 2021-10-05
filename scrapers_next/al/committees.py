from spatula import URL, CSS, HtmlListPage, HtmlPage
from openstates.models import ScrapeCommittee
import re


class CommDetail(HtmlPage):
    def process_page(self):
        com = self.input

        members = CSS("table.Grid a").match(self.root)
        for member in members:
            name = member.text_content().strip()
            if re.search(r"\(", name):
                name_split = re.search(r"(.+),\s(.+)\s\((.+)\)", name).groups()
                first_name = name_split[1]
                last_name = name_split[0]
                role = name_split[2]
            else:
                name_split = re.search(r"(.+),\s(.+)", name).groups()
                first_name = name_split[1]
                last_name = name_split[0]
                role = "member"
            first_name = re.sub("&quot", '"', first_name)
            name = f"{first_name} {last_name}"

            com.add_member(name, role)

        extra_info = CSS("div table#ContentPlaceHolder1_gvClerk tr").match(self.root)
        for info in extra_info:
            if ":" in info.text_content().strip():
                idx, val = info.text_content().strip().split(":")
                com.extras[idx.strip()] = val.strip()
            else:
                 com.extras["Room"] = info.text_content().strip()

        return com


class CommList(HtmlListPage):
    def process_item(self, item):
        comm_name = item.text_content().strip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber=self.chamber,
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)

        # detail links for Joint Committees are hidden
        # "javascript:__doPostBack('ctl00$ContentPlaceHolder1$gvJICommittees','cmdCommittee$0')"
        if self.chamber != "legislature":
            com.add_source(detail_link)
            com.add_link(detail_link, note="homepage")

            return CommDetail(com, source=detail_link)
        return com


class Senate(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/senate/SenateCommittees.aspx"
    )
    chamber = "upper"
    selector = CSS("li.interim_listpad a")


class House(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/House/HouseCommittees.aspx"
    )
    chamber = "lower"
    selector = CSS("li.interim_listpad a")


class Joint(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/House/JointInterimCommittees.aspx"
    )
    chamber = "legislature"
    selector = CSS("tr td a")
