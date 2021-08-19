from spatula import URL, HtmlListPage, XPath, HtmlPage, CSS
from openstates.models import ScrapeCommittee
import re
from dataclasses import dataclass


@dataclass
class PartialSubCommittee:
    chamber: str
    source1: str
    source2: str
    link: str


class SubCommitteeDetail(HtmlPage):
    input_type = PartialSubCommittee

    def process_page(self):
        parent = CSS("font").match(self.root)[1].text_content().strip()
        parent = re.search(
            r"(House|Senate)\s(.+)\s(Subcommittee\sMembers)", parent
        ).groups()[1]

        sub_dict = {}
        titles_dict = {}
        members_dict = {}

        # grab all subcommittee titles
        for num, title in enumerate(
            XPath(
                "/html/body/div/table/tr[7]/td[2]/table/tr[3]/td/div/table/tr/td/table/tr/td/div/strong"
            ).match(self.root)
        ):
            title_clean = ""
            title = title.text_content().strip()
            if title != "":
                for word in title.split():
                    title_clean += word.lower().capitalize()
                    title_clean += " "
                titles_dict[num] = title_clean.strip()

        # grab all subcommittee members
        for num, members in enumerate(
            XPath(
                "/html/body/div/table/tr[7]/td[2]/table/tr[3]/td/div/table/tr/td/table/tr/td/div/p"
            ).match(self.root)
        ):
            if members.text_content().strip() != "":
                members_dict[num] = members.text_content().strip()

        # combine titles and members into 1 dict
        for title in range(len(titles_dict)):
            if re.search(r"Rep\.\s", members_dict[title]):
                sub_dict[titles_dict[title]] = members_dict[title].split("Rep. ")
            else:
                sub_dict[titles_dict[title]] = members_dict[title].split("Sen. ")

        # create ScrapeCommittee() for each subcommittee, add each member
        for title, members in sub_dict.items():
            com = ScrapeCommittee(
                name=title,
                chamber=self.input.chamber,
                classification="subcommittee",
                parent=parent,
            )
            com.add_source(self.input.source1)
            com.add_source(self.input.source2)
            com.add_link(self.input.source2, note="homepage")

            for member in members:
                if member.strip() == "":
                    continue
                elif ";" in member:
                    member_name = member.split(";")[0].strip()
                    member_role = member.split(";")[1].strip()
                else:
                    member_name = member.strip()
                    member_role = "member"
                com.add_member(member_name, member_role)
            yield com


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        extra_info = (
            XPath(
                "/html/body/div/table/tr[7]/td[2]/table/tr[2]/td/div/table/tr/td/div/table"
            )
            .match_one(self.root)
            .getchildren()
        )
        for line in extra_info:
            line = line.text_content().strip()
            title, info = re.search(r"(.+):\s(.+)", line).groups()
            if info != "--":
                com.extras[title] = info

        members = XPath(
            "/html/body/div/table/tr[7]/td[2]/table/tr[2]/td/div/table/tr/td/table/tr"
        ).match(self.root)
        for member in members:
            if member.get("class") == "bodyCopyBL":
                continue

            name = CSS("td div").match(member)[0].text_content().strip()
            name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]
            role = CSS("td div").match(member)[1].text_content().strip()
            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.rilegislature.gov/pages/committees.aspx")

    def process_item(self, item):
        name = item.text_content().strip()

        if re.search(r"Subcommittees", name):
            source = item.get("href")

            sub = PartialSubCommittee(
                chamber=self.chamber,
                source1=self.source.url,
                source2=source,
                link=source,
            )
            return SubCommitteeDetail(
                sub,
                source=source,
            )

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        com.add_source(self.source.url)
        source = item.get("href")
        com.add_source(source)
        com.add_link(source, note="homepage")

        return CommitteeDetail(
            com,
            source=source,
        )


class House(CommitteeList):
    chamber = "lower"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{811ABDBE-2D09-4586-8D38-D18203BD2C7E}']//a"
    )


class Senate(CommitteeList):
    chamber = "upper"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{733ACC1D-0F41-4EB2-ABC2-0E815521BD5E}']//a"
    )


class Joint(CommitteeList):
    chamber = "legislature"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{E09F0FD2-B6DF-4422-8B22-FBF09B2C85EB}']//a"
    )
