import lxml.html
import datetime as dt
from fiftystates.scrape import NoDataForYear

from fiftystates.scrape.committees import CommitteeScraper, Committee

# TODO scrape assembly subcommittees

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

        with self.urlopen(assembly_committees_url) as html:
            doc = lxml.html.fromstring(html)
            standing_committees, subcommittees, legislative_commissions, task_forces = doc.cssselect('#sitelinks ul')
            committee_paths = set([l.get('href') for l in standing_committees.cssselect("li a[href]")
                              if l.get("href").startswith('?sec=mem')])

        for committee_path in committee_paths:
            committee_url = assembly_committees_url+committee_path
            with self.urlopen(committee_url) as chtml:
                cdoc = lxml.html.fromstring(chtml)
                for h in cdoc.cssselect("#content .pagehdg"):
                    if h.text:
                        committee_name = h.text.split('Committee Members')[0].strip()
                        break

                committee = Committee("lower", committee_name)
                committee.add_source(committee_url)
                members = cdoc.cssselect("#sitelinks")[0]

                first = 1
                for member in members.iter('span'):
                    member = member.xpath('li/a')[0].text
                    if first == 1:
                        committee.add_member(member, 'chair')
                        first = 0
                    else:
                        committee.add_member(member)

                self.save_committee(committee)

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
