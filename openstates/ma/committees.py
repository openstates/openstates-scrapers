from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class MACommitteeScraper(CommitteeScraper):
    jurisdiction = 'ma'

    def scrape(self, term, chambers):
        page_types = []
        if 'upper' in chambers:
            page_types += ['Senate', 'Joint']
        if 'lower' in chambers:
            page_types += ['House']
        chamber_mapping = {'Senate': 'upper',
                           'House': 'lower',
                           'Joint': 'joint'}

        for page_type in page_types:
            url = 'http://www.malegislature.gov/Committees/' + page_type

            html = self.get(url, verify=False).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute('http://www.malegislature.gov')

            for com_url in doc.xpath('//ul[@class="committeeList"]/li/a/@href'):
                chamber = chamber_mapping[page_type]
                self.scrape_committee(chamber, com_url)

    def scrape_committee(self, chamber, url):
        html = self.get(url, verify=False).text
        doc = lxml.html.fromstring(html)

        name = doc.xpath('//title/text()')[0]
        com = Committee(chamber, name)
        com.add_source(url)

        members = doc.xpath('//a[contains(@href, "/Legislators/Profile")]')
        for member in members:
            title = member.xpath('../span')
            role = title[0].text.lower() if title else 'member'
            com.add_member(member.text, role)

        if com['members']:
            self.save_committee(com)
