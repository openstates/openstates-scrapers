from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee 

import lxml.html
import re

class WYCommitteeScraper(CommitteeScraper):
    state = "wy"

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
        with self.urlopen(list_url) as page:
            page = lxml.html.fromstring(page)
            for el in page.xpath(".//a[contains(@href, 'CommitteeMembers')]"):
                committees[el.text] = el.get("href")

        for c in committees:
            self.log(c)
            detail_url = self.urls["detail"] % (committees[c],)
            with self.urlopen(detail_url) as page:
                page = lxml.html.fromstring(page)
                for table in page.xpath(".//table[contains(@id, 'CommitteeMembers')]"):
                    rows = table.xpath(".//tr")
                    chamber = rows[0].xpath('.//td')[0].text_content().strip()
                    chamber = 'upper' if self.log(chamber) == 'Senator' else 'lower'
                    comm = Committee(chamber, c)
                    for row in rows[1:]:
                        tds = row.xpath('.//td')
                        name = tds[0].text_content().strip()
                        role = 'chairman' if tds[3].text_content().strip() == 'Chairman' else 'member'
                        self.log(name)
                        self.log(role)
                        comm.add_member(name, role)
                    self.save_committee(comm)
