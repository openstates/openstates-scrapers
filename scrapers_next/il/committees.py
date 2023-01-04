from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class SenDetail(HtmlPage):
    def process_page(self):
        com = self.input
        # the member page for joint commissions is slightly different
        if list(com)[1][1] != "upper":
            try:
                members = CSS(".content").match(self.root)
            except SelectorError:
                raise SkipItem("empty committee")

            members = [
                i.text.split(",")[0].strip() for i in members
            ]  # cleaning up member names
            roles = CSS(".heading").match(self.root)
            roles = [i.text for i in roles][
                1:
            ]  # the first "role" is the name of the committee

            for i in range(len(roles)):
                com.add_member(members[i], roles[i])

        else:
            try:
                members = CSS(".notranslate").match(self.root)

            except SelectorError:
                raise SkipItem("empty committee")

            roles = CSS(".heading").match(self.root)

            members = [i.text for i in members if i.text != "D"]
            members = [i for i in members if i != "R"]
            roles = [i.text.split()[0].strip().strip(":") for i in roles][1:]

            for i in range(len(roles)):
                com.add_member(members[i], roles[i])

        return com


class SenList(HtmlListPage):
    source = URL("https://www.ilga.gov/senate/committees/default.asp")
    selector = CSS(".content")

    def process_item(self, item):
        # committee codes dictionary used to map subcommittees to parent committees
        comm_codes_dict = {
            "SAPP": "Appropriations",
            "SCCL": "Criminal Law",
            "SENE": "Energy and Public Utilities",
            "SEXC": "Executive",
            "SHEA": "Health",
            "SINS": "Insurance",
            "SJUD": "Judiciary",
            "SLAB": "Labor",
            "SLIC": "Licensed Activities",
            "SRED": "Redistricting",
            "SREV": "Revenue",
            "STRN": "Transportation",
        }

        if item.getchildren():
            comm = item.getchildren()[0]
            comm_name = comm.text
            comm_code = [i.text for i in item.itersiblings()][0]

            # random, non-committee link that's on the page
            if comm_name == "Reports":
                raise SkipItem("not a committee")

            # regular committees
            if comm_code != "Not Scheduled":
                chamber = "upper"

                # identifying subcommittees
                if "-" in comm_code:
                    this_committee_code = comm_code.split("-")[0]
                    parent_committee = comm_codes_dict[this_committee_code]

                    com = ScrapeCommittee(
                        name=comm_name,
                        classification="subcommittee",
                        chamber=chamber,
                        parent=parent_committee,
                    )

                else:
                    com = ScrapeCommittee(
                        name=comm_name,
                        classification="committee",
                        chamber=chamber,
                    )

            # joint commissions
            else:
                chamber = "legislature"
                com = ScrapeCommittee(
                    name=comm_name,
                    classification="committee",
                    chamber=chamber,
                )

            detail_link = comm.get("href")
            com.add_source(self.source.url, note="homepage")
            com.add_source(detail_link)

            return SenDetail(com, source=detail_link)

        else:
            self.skip()


class HouseDetail(HtmlPage):
    def process_page(self):
        com = self.input
        # the member page for joint commissions is slightly different
        if list(com)[1][1] != "lower":
            try:
                members = CSS(".content").match(self.root)
            except SelectorError:
                raise SkipItem("empty committee")

            members = [
                i.text.split(",")[0].strip() for i in members
            ]  # cleaning up member names
            roles = CSS(".heading").match(self.root)
            roles = [i.text for i in roles][
                1:
            ]  # the first "role" is the name of the committee

            for i in range(len(roles)):
                com.add_member(members[i], roles[i])

        else:
            try:
                members = CSS(".notranslate").match(self.root)

            except SelectorError:
                raise SkipItem("empty committee")

            roles = CSS(".heading").match(self.root)

            members = [i.text for i in members if i.text != "D"]
            members = [i for i in members if i != "R"]
            roles = [i.text.split()[0].strip().strip(":") for i in roles][1:]

            for i in range(len(roles)):
                com.add_member(members[i], roles[i])

        return com


class HouseList(HtmlListPage):
    source = URL("https://www.ilga.gov/house/committees/default.asp")
    selector = CSS(".content")

    def process_item(self, item):
        # committee codes dictionary used to map subcommittees to parent committees
        comm_codes_dict = {
            "HAPI": "Appropriations- Higher Education",
            "HAPH": "Appropriations- Human Services",
            "HCIV": "Cities & Villages",
            "HCON": "Consumer Protection",
            "HENG": "Energy & Environment",
            "SHEE": "Ethics & Elections Committee",
            "HFIN": "Financial Institutions",
            "HHSV": "Human Services",
            "HINS": "Insurance",
            "HJUA": "Judiciary- Civil",
            "HJUC": "Judiciary- Criminal",
            "HLBR": "Labor & Commerce",
            "HMEH": "Mental Health & Addiction",
            "HMAC": "Museums, Arts, & Cultural Enhancement",
            "HPPN": "Personnel & Pensions",
            "SHPF": "Police & Fire Committee",
            "HPUB": "Public Utilities",
            "HREF": "Revenue & Finance",
            "HSGA": "State Government Administration",
            "HTRR": "Transportation: Regulation, Roads",
            "HVES": "Transportation: Vehicles & Safety",
        }

        if item.getchildren():
            comm = item.getchildren()[0]
            comm_name = comm.text
            comm_code = [i.text for i in item.itersiblings()][0]

            # random, non-committee link that's on the page
            if comm_name == "Reports":
                raise SkipItem("not a committee")

            # regular committees
            if comm_code != "Not Scheduled":
                chamber = "lower"

                # identifying subcommittees
                if "-" in comm_code:
                    this_committee_code = comm_code.split("-")[0]
                    parent_committee = comm_codes_dict[this_committee_code]

                    com = ScrapeCommittee(
                        name=comm_name,
                        classification="subcommittee",
                        chamber=chamber,
                        parent=parent_committee,
                    )

                else:
                    com = ScrapeCommittee(
                        name=comm_name,
                        classification="committee",
                        chamber=chamber,
                    )

            # we don't include task forces
            elif "Task Force" in comm_name:
                self.skip()

            # joint commissions
            else:
                chamber = "legislature"
                com = ScrapeCommittee(
                    name=comm_name,
                    classification="committee",
                    chamber=chamber,
                )

            detail_link = comm.get("href")
            com.add_source(self.source.url, note="homepage")
            com.add_source(detail_link)

            return HouseDetail(com, source=detail_link)

        else:
            self.skip()
