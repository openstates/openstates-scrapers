from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html
import re

class WYCommitteeScraper(CommitteeScraper):
    jurisdiction = "wy"

    members = {}
    urls = {
            "list": "http://legisweb.state.wy.us/LegbyYear/CommitteeList.aspx?Year=%s",
            "detail": "http://legisweb.state.wy.us/LegbyYear/%s"
    }

    def scrape(self, chamber, term):
        if chamber == 'lower':
            # Committee members from both houses are listed
            # together. So, we'll only scrape once.
            return None

        year = None

        # Even thought each term spans two years, committee
        # memberships don't appear to change. So we only
        # need to scrape the first year of the term.
        for t in self.metadata["terms"]:
            if term == t["name"]:
                year = t["start_year"]
                break

        if not year:
            raise NoDataForPeriod(term)


        list_url = self.urls["list"] % (year, )
        committees = {}
        page = self.urlopen(list_url)
        page = lxml.html.fromstring(page)
        for el in page.xpath(".//a[contains(@href, 'CommitteeMembers')]"):
            committees[el.text.strip()] = el.get("href")

        for c in committees:
            self.log(c)
            detail_url = self.urls["detail"] % (committees[c],)
            page = self.urlopen(detail_url)
            page = lxml.html.fromstring(page)
            if re.match('\d{1,2}-', c):
                c = c.split('-', 1)[1]
            comm = Committee('joint', c.strip())
            for table in page.xpath(".//table[contains(@id, 'CommitteeMembers')]"):
                rows = table.xpath(".//tr")
                chamber = rows[0].xpath('.//td')[0].text_content().strip()
                chamber = 'upper' if chamber == 'Senator' else 'lower'
                for row in rows[1:]:
                    tds = row.xpath('.//td')
                    name = tds[0].text_content().strip()
                    role = 'chairman' if tds[3].text_content().strip() == 'Chairman' else 'member'
                    comm.add_member(name, role, chamber=chamber)

            comm.add_source(detail_url)
            self.save_committee(comm)
