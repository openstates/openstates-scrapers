from lxml.html import fromstring
from lxml.html.clean import Cleaner
from lxml.etree import ParserError
from spatula import JsonListPage, URL
import logging
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
                logging.warning(f"No membership data found for: {name}")
                continue

            cleaner = Cleaner(allow_tags=[""], remove_unknown_tags=False)
            members_list = cleaner.clean_html(doc).text_content()

            name = (
                name.lower().replace("house", "").replace("senate", "").strip().title()
            )
            com = ScrapeCommittee(
                name=name,
                chamber=chamber,
                parent=parent,
                classification=classification,
            )

            for member in members_list.splitlines():
                if not member.strip():
                    logging.warning(f"No membership data found for: {name}")
                    continue
                try:
                    member = member.lower().replace("rep.", "").replace("sen.", "")
                    splits = member.split(",")
                    member_name = splits[0]
                    role = " ".join(splits[1 : len(splits)]).strip()
                except IndexError:
                    member_name = member
                    role = "Member"

                if (not role) or ("member" in role.lower()):
                    role = "Member"
                member_name = member_name.replace(".", "")
                com.add_member(member_name.strip().title(), role=role.strip().title())

            # additional check if no member found
            if not com.members:
                logging.warning(f"No membership data found for: {name}")
                continue
            if each_committee.get("WebSiteURL"):
                com.add_link(each_committee["WebSiteURL"], note="Committee web page")
            if each_committee.get("StreamingURL"):
                com.add_link(
                    each_committee["WebSiteURL"], note="Committee streaming page"
                )

            com.add_source(
                self.source.url,
                note="Committee JSON from legislature.vermont.gov site",
            )
            yield com
