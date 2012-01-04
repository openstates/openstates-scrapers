from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class HICommitteeScraper(CommitteeScraper):
    state = 'hi'
    latest_only = True

    def scrape(self, chamber, term):
        urls = {'lower': 'http://www.capitol.hawaii.gov/session2011/HouseCommittees/housecommittees.aspx',
                'upper': 'http://www.capitol.hawaii.gov/session2011/senatecommittees/committeepage.aspx?committee=AGL'}

        url = urls[chamber]

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            for a in doc.xpath('//a[contains(@id, "HyperLinkCommName")]'):
                com = Committee(chamber, a.text_content())
                self.scrape_committee(com, a.get('href'))
                self.save_committee(com)


    def scrape_committee(self, committee, url):
        committee.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            chair = doc.xpath('//a[@id="HyperLinkChair"]/text()')[0].strip()
            vchair = doc.xpath('//a[@id="HyperLinkcvChair"]/text()')[0].strip()
            committee.add_member(chair, role='chair')
            committee.add_member(vchair, role='vice chair')

            for m in doc.xpath('//a[contains(@id, "HyperLinkMember")]/text()'):
                committee.add_member(m)


