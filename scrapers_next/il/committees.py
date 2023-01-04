from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class SenDetail(HtmlPage):
    def process_page(self):
        com = self.input
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
                raise SkipItem

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
            com.add_source(self.source.url)
            com.add_source(detail_link)

            return SenDetail(com, source=detail_link)

        else:
            self.skip()


"""
    def process_page(self):
        comm_codes_dict = {"SAPP":"Appropriations", "SCCL": "Criminal Law", "SENE": "Energy and Public Utilities",
                           "SEXC": "Executive", "SHEA": "Health", "SINS": "Insurance", "SJUD": "Judiciary",
                           "SLAB": "Labor", "SLIC": "Licensed Activities", "SRED": "Redistricting", "SREV": "Revenue",
                           "STRN": "Transportation"}

        comm_codes = CSS(".content").match(self.root)
        comm_codes = ([i.text for i in comm_codes if i.text is not None])
        comm_codes = [i.strip() for i in comm_codes if i.startswith("S")]
        print(comm_codes)


        comms = CSS(".content a").match(self.root)
        comm_names = [i.text.strip() for i in comms]

        #print(len(comm_codes), "CODE LEN")
        #print(len(comm_names), "NAME LEN")

        for i in range(len(comm_names)):
            committee_name = comm_names[i]
            #regular committees
            if i <= 102:
                chamber = "upper"
                committee_code = comm_codes[i]

                # random, non-committee link that's on the page
                if committee_name == "Reports":
                    continue

                # identifying subcommittees
                if "-" in committee_code:
                    comm_code = committee_code.split("-")[0]
                    parent_committee = comm_codes_dict[comm_code]

                    com = ScrapeCommittee(
                        name=committee_name,
                        classification="subcommittee",
                        chamber=chamber,
                        parent=parent_committee
                    )

                else:
                    com = ScrapeCommittee(
                        name=committee_name,
                        classification="committee",
                        chamber=chamber,
                    )


            # joint commissions
            else:
                chamber = "legislature"
                com = ScrapeCommittee(
                    name=committee_name,
                    classification="committee",
                    chamber=chamber,
                )

            detail_link = comms[i].get("href")
            com.add_source(self.source.url)
            com.add_source(detail_link)

            return SenDetail(com, source=detail_link)
"""
