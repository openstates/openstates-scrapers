from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class WICommitteeScraper(CommitteeScraper):
    jurisdiction = 'wi'

    def scrape_committee(self, name, url, chamber):
        com = Committee(chamber, name)
        com.add_source(url)
        data = self.get(url).text
        doc = lxml.html.fromstring(data)

        for leg in doc.xpath('//div[@id="members"]/div[@id="members"]/p/a/text()'):
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
        for chamber in chambers+["joint"]:
            url = 'http://docs.legis.wisconsin.gov/2015/committees/'
            if chamber == 'joint':
                url += "joint"
            elif chamber == 'upper':
                url += 'senate'
            else:
                url += 'assembly'
            data = self.get(url).text
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(url)

            for a in doc.xpath('//ul[@class="docLinks"]/li/p/a'):
                if "(Disbanded" not in a.text:
                    comm_name = a.text
                    comm_name = comm_name.replace("Committee on", "")
                    comm_name = comm_name.replace("Assembly", "")
                    comm_name = comm_name.replace("Joint Survey", "")
                    comm_name = comm_name.replace("Joint Review", "")
                    comm_name = comm_name.replace("Joint", "")
                    comm_name = comm_name.replace("Senate", "")
                    comm_name = comm_name.replace("Committee for", "")
                    comm_name = comm_name.replace("Committee", "")
                    comm_name = comm_name.strip()
                    self.scrape_committee(comm_name, a.get('href'), chamber)
