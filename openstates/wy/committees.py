import re

import lxml.html
from pupa.scrape import Scraper, Organization


class WYCommitteeScraper(Scraper):
    members = {}
    urls = {
        "list": "http://legisweb.state.wy.us/LegbyYear/CommitteeList.aspx?Year=%s",
        "detail": "http://legisweb.state.wy.us/LegbyYear/%s",
    }

    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        list_url = self.urls["list"] % (session, )
        committees = {}
        page = self.get(list_url).text
        page = lxml.html.fromstring(page)
        for el in page.xpath(".//a[contains(@href, 'CommitteeMembers')]"):
            committees[el.text.strip()] = el.get("href")

        for c in committees:
            self.info(c)
            detail_url = self.urls["detail"] % (committees[c],)
            page = self.get(detail_url).text
            page = lxml.html.fromstring(page)
            if re.match('\d{1,2}-', c):
                c = c.split('-', 1)[1]
            jcomm = Organization(name=c.strip(), chamber='joint', classification='committee')
            for table in page.xpath(".//table[contains(@id, 'CommitteeMembers')]"):
                rows = table.xpath(".//tr")
                chamber = rows[0].xpath('.//td')[0].text_content().strip()
                chamber = 'upper' if chamber == 'Senator' else 'lower'
                comm = Organization(name=c.strip(), chamber=chamber, classification='committee')
                for row in rows[1:]:
                    tds = row.xpath('.//td')
                    name = tds[0].text_content().strip()
                    role = 'chairman' if tds[3].text_content().strip() == 'Chairman' else 'member'
                    comm.add_member(name, role)
                    jcomm.add_member(name, role)

                comm.add_source(detail_url)
                yield comm

            jcomm.add_source(detail_url)
            yield jcomm
