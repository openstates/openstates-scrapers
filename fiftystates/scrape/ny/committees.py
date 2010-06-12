import lxml.html
import datetime as dt

from fiftystates.scrape.committees import CommitteeScraper, Committee

class NYCommitteeScraper(CommitteeScraper):
    state = "ny"

    def scrape(self, chamber, year):
        # Data available for this year only
        if int(year) != dt.date.today().year:
            raise NoDataForYear(year)

        if chamber == "upper":
            self.scrape_senate()
        elif chamber == "lower":
            self.scrape_assembly()

    def scrape_assembly(self):
        """Scrape Assembly Committees"""
        assembly_committees_url = "http://assembly.state.ny.us/comm/"

    def scrape_senate(self):
        """Scrape Senate Committees"""
        senate_url = "http://www.nysenate.gov"
        senate_committees_url = senate_url + "/committees"

        with self.urlopen(senate_committees_url) as html:
            doc = lxml.html.fromstring(html)
            committee_paths = set([l.get("href") for l in doc.cssselect("li a")
                              if l.get("href", "").find("/committee/") != -1])

        for committee_path in committee_paths:
            committee_url = senate_url+committee_path
            with self.urlopen(committee_url) as chtml:
                cdoc = lxml.html.fromstring(chtml)
                for h in cdoc.cssselect(".committee_name"):
                    if h.text:
                        committee_name = h.text
                        break

                committee = Committee("upper", committee_name)
                committee.add_source(committee_url)
                for l in cdoc.cssselect(".committee-chair a[href]"):
                    if "/senator/" in l.get("href") and l.text and l.text.startswith("Sen."):
                        committee.add_member(l.text.split('Sen. ', 1)[1], "chair")

                for l in cdoc.cssselect(".committee-members a[href]"):
                    if "/senator/" in l.get("href"):
                        committee.add_member(l.text)

                self.save_committee(committee)
