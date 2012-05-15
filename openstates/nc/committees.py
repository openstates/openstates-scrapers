from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class NCCommitteeScraper(CommitteeScraper):
    state = 'nc'

    def scrape_committee(self, committee, url):
        url = url.replace(' ', '%20') + '&bPrintable=true'
        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            for row in doc.xpath('//table/tr'):
                children = row.getchildren()
                if len(children) != 2:
                    self.log('skipping members for ' + committee['committee'])
                    continue
                mtype, members = row.getchildren()
                if mtype.text == 'Members':
                    for m in members.getchildren():
                        committee.add_member(m.text)
                else:
                    committee.add_member(members.text_content(), mtype.text)


    def scrape(self, term, chambers):
        base_url = 'http://www.ncga.state.nc.us/gascripts/Committees/Committees.asp?bPrintable=true&sAction=ViewCommitteeType&sActionDetails='

        chamber_slugs = {'upper': ['Senate%20Standing', 'Senate%20Select'],
                         'lower': ['House%20Standing', 'House%20Select']}

        for chamber in chambers:
            for ctype in chamber_slugs[chamber]:
                data = self.urlopen(base_url + ctype)
                doc = lxml.html.fromstring(data)
                doc.make_links_absolute(base_url+ctype)
                for comm in doc.xpath('//ul/li/a'):
                    name = comm.text
                    url = comm.get('href')
                    committee = Committee(chamber, name)
                    self.scrape_committee(committee, url)
                    committee.add_source(url)
                    self.save_committee(committee)

