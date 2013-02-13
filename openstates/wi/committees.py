from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class WICommitteeScraper(CommitteeScraper):
    jurisdiction = 'wi'

    def scrape_committee(self, name, url, chamber):
        com = Committee(chamber, name)
        com.add_source(url)
        data = self.urlopen(url)
        doc = lxml.html.fromstring(data)

        for leg in doc.xpath('//a[contains(@href, "leg-info")]/text()'):
            leg = leg.replace('Representative ', '')
            leg = leg.replace('Senator ', '')
            leg = leg.strip()
            if ' (' in leg:
                leg, role = leg.split(' (')
                if 'Vice-Chair' in role:
                    role = 'vice-chair'
                elif 'Co-Chair' in role:
                    role = 'co-chair'
                elif 'Chair' in role:
                    role = 'chair'
                else:
                    raise Exception('unknown role: %s' % role)
            else:
                role = 'member'
            com.add_member(leg, role)

        self.save_committee(com)


    def scrape(self, term, chambers):
        for chamber in chambers:
            url = 'http://legis.wisconsin.gov/Pages/comm-list.aspx?h='
            url += 's' if chamber == 'upper' else 'a'
            data = self.urlopen(url)
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(url)

            table = doc.xpath('//table[@class="commList"]')[0]
            for a in table.xpath('.//a[contains(@href, "comm-info")]'):
                self.scrape_committee(a.text, a.get('href'), chamber)

            # also scrape joint committees (once, only on upper)
            if chamber == 'upper':
                table = doc.xpath('//table[@class="commList"]')[1]
                for a in table.xpath('.//a[contains(@href, "comm-info")]'):
                    self.scrape_committee(a.text, a.get('href'), 'joint')
