from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class ChamberDetail(HtmlPage):
    def process_page(self):
        com = self.input

        try:
            members = CSS(".notranslate").match(self.root)

        except SelectorError:
            raise SkipItem("empty committee")

        roles = CSS(".heading").match(self.root)

        members = [i.text for i in members if i.text != "D"]
        members = [i for i in members if i != "R"]

        # joint committee roles are formatted slightly differently
        if "Joint Committee" in list(com)[0][1]:
            roles = [i.text.split(":")[0].strip() for i in roles][1:]
            roles = [i for i in roles if i != ""]
        else:
            roles = [i.text.split()[0].strip().strip(":") for i in roles][1:]

        for i in range(len(roles)):
            com.add_member(members[i], roles[i])

        return com


class SenateList(HtmlListPage):
    source = URL("https://www.ilga.gov/senate/committees/default.asp")
    selector = CSS(".content")

    def process_item(self, item):
        # committee codes dictionary used to map subcommittees to parent committees
        comm_codes_dict = {
            "APED": "Approp Ed",
            "SAPP": "Appropriations",
            "SCCL": "Criminal Law",
            "SENE": "Energy and Public Utilities",
            "SEXC": "Executive",
            "SFIC": "Financial Institutions",
            "SHEA": "Health",
            "SINS": "Insurance",
            "SGOA": "State Government",
            "SJUD": "Judiciary",
            "SLAB": "Labor",
            "SLIC": "Licensed Activities",
            "SRED": "Redistricting",
            "SREV": "Revenue",
            "SSCC": "Criminal Law & Public Safety",
            "SSCP": "Pensions",
            "STRN": "Transportation",
            "SVET": "Veterans Affairs",
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
                detail_link = comm.get("href")
                com.add_source(self.source.url, note="homepage")
                com.add_source(detail_link)

                return ChamberDetail(com, source=detail_link)

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

                return JointCommissionDetail(com, source=detail_link)

        else:
            self.skip()


class HouseList(HtmlListPage):
    source = URL("https://www.ilga.gov/house/committees/default.asp")
    selector = CSS(".content")

    def process_item(self, item):
        # committee codes dictionary used to map subcommittees to parent committees
        comm_codes_dict = {
            "HACW": "Adoption & Child Welfare",
            "HAGC": "Agriculture & Conservation",
            "HAPI": "Appropriations- Higher Education",
            "HAPH": "Appropriations- Health & Human Services",
            "HAPP": "Appropriations- Public Safety",
            "HCIV": "Cities & Villages",
            "HCON": "Consumer Protection",
            "HENG": "Energy & Environment",
            "HELO": "Elementary & Secondary Education",
            "SHEE": "Ethics & Elections Committee",
            "HFIN": "Financial Institutions",
            "HHCA": "Health Care Availability & Accessibility",
            "HEXC": "Executive",
            "HHCL": "Health Care Licenses",
            "HHED": "Higher Education",
            "HHSV": "Human Services",
            "HINS": "Insurance",
            "HJUA": "Judiciary- Civil",
            "HJUC": "Judiciary- Criminal",
            "HLBR": "Labor & Commerce",
            "HMEH": "Mental Health & Addiction",
            "HMAC": "Museums, Arts, & Cultural Enhancement",
            "HPPN": "Personnel & Pensions",
            "SHPF": "Police & Fire Committee",
            "HPDA": "Prescription Drug Affordability",
            "HPUB": "Public Utilities",
            "HREF": "Revenue & Finance",
            "HSGA": "State Government Administration",
            "HTRR": "Transportation: Regulations, Roads & Bridges",
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

                detail_link = comm.get("href")
                com.add_source(self.source.url, note="homepage")
                com.add_source(detail_link)

                return ChamberDetail(com, source=detail_link)

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

                return JointCommissionDetail(com, source=detail_link)

        else:
            self.skip()


# this is the logic for chamber joint commission pages (not joint committee)
class JointCommissionDetail(HtmlPage):
    def process_page(self):
        com = self.input
        try:
            members = CSS(".content").match(self.root)
        except SelectorError:
            raise SkipItem("empty committee")

        members = [
            i.text.split(",")[0].strip() for i in members
        ]  # cleaning up member names
        roles = CSS(".heading").match(self.root)
        # the first "role" is the name of the committee
        roles = [i.text for i in roles][1:]

        for i in range(len(roles)):
            com.add_member(members[i], roles[i])
        return com


class JointCommittee(HtmlListPage):
    source = URL("https://www.ilga.gov/joint/JointCommittees.asp")
    selector = CSS("p a")

    def process_item(self, item):
        comm_name = item.text_content().strip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber="legislature",
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return ChamberDetail(com, source=detail_link)
