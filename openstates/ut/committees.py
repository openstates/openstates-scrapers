from pupa.scrape import Scraper, Organization


class UTCommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        committees_url = "http://le.utah.gov/data/committees.json"
        committees = self.get(committees_url).json()["committees"]

        people_url = "http://le.utah.gov/data/legislators.json"
        people = self.get(people_url).json()["legislators"]

        # The committee JSON only has legislator IDs, not names
        ids_to_names = {}
        for person in people:
            ids_to_names[person["id"]] = person["formatName"]

        for committee in committees:
            name = committee["description"]
            if name.endswith(" Committee"):
                name = name[: len(name) - len(" Committee")]
            elif name.endswith(" Subcommittee"):
                name = name[: len(name) - len(" Subcommittee")]
            if name.startswith("House "):
                name = name[len("House ") :]
                chamber = "lower"
            elif name.startswith("Senate "):
                name = name[len("Senate ") :]
                chamber = "upper"
            else:
                chamber = "legislature"

            c = Organization(chamber=chamber, name=name, classification="committee")
            c.add_source(committees_url)
            c.add_source(people_url)
            c.add_link(committee["link"])

            for member in committee["members"]:
                try:
                    member_name = ids_to_names[member["id"]]
                except KeyError:
                    self.warning(
                        "Found unknown legislator ID in committee JSON: " + member["id"]
                    )
                c.add_member(member_name, role=member["position"])

            yield c
