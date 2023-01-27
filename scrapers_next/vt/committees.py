from lxml.html import fromstring
from lxml.html.clean import Cleaner
from lxml.etree import ParserError
from spatula import JsonListPage, URL, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeList(JsonListPage):
    source = URL(
        "https://legislature.vermont.gov/committee/loadList/2024/",
        timeout=10,
    )

    def process_page(self):
        for each_committee in self.response.json()["data"]:
            # name
            name = each_committee["LongName"]

            # chamber
            if "house" in name.lower():
                chamber = "lower"
            elif "senate" in name.lower():
                chamber = "upper"
            else:
                chamber = "legislature"

            # classification & parent check
            classification = "committee"
            parent = None
            if "subcommittee" in name.lower():
                classification = "subcommittee"
                parent = name.lower().split()[-1].replace(")", "")

            # extracting members
            members_html = each_committee["Members"].strip()
            members_html = members_html.replace("</br>", "\n")
            try:
                doc = fromstring(members_html)
            except ParserError:
                SkipItem(f"No membership data found for: {name}")
                continue

            cleaner = Cleaner(allow_tags=[""], remove_unknown_tags=False)
            members_list = cleaner.clean_html(doc).text_content()

            com = ScrapeCommittee(
                name=name,
                chamber=chamber,
                parent=parent,
                classification=classification,
            )

            for member in members_list.splitlines():
                if not member.strip():
                    SkipItem(f"No membership data found for: {name}")
                    continue
                try:
                    name, role = member.split(",")
                except ValueError:
                    name = member
                    role = "Member"
                com.add_member(name.strip().title(), role=role.strip().title())

            # additional check if no member found
            if not com.members:
                SkipItem(f"No membership data found for: {name}")
                continue

            com.add_source(
                self.source.url,
                note="Committee json  of legislature.vermont.gov site",
            )
            yield com
