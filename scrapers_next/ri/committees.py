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
        titles = {}
        members_dict = {}
        for count, td in enumerate(
            XPath(
                "/html/body/div/table/tr[7]/td[2]/table/tr[3]/td/div/table/tr/td/table/tr/td"
            ).match(self.root)
        ):
            if td.text_content().strip() != "":
                if re.search(
                    r"(Rep|Sen)\.\s", CSS("div strong").match_one(td).text_content()
                ):
                    members_dict[count] = td.text_content().strip()
                else:
                    titles[count] = td.text_content().strip().lower().capitalize()

        parent = CSS("font").match(self.root)[1].text_content().strip()
        parent = re.search(
            r"(House|Senate)\s(.+)\s(Subcommittee\sMembers)", parent
        ).groups()[1]

        for title_count, title in enumerate(titles.values()):
            com = ScrapeCommittee(
                name=title,
                chamber=self.input.chamber,
                classification="subcommittee",
                parent=parent,
            )
            com.add_source(self.input.source1)
            com.add_source(self.input.source2)
            com.add_link(self.input.source2, note="homepage")

            for mem_count, members in enumerate(members_dict.values()):
                if title_count == mem_count:
                    if re.search(r"Rep\.\s", members):
                        members = members.split("Rep. ")
                    else:
                        members = members.split("Sen. ")

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
        name = item.text_content()

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

        # need to do in subcommittees as well
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
