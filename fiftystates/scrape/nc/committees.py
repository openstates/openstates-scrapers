from fiftystates.scrape.committees import CommitteeScraper, Committee

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
                    members = members.text_content().split(', ')
                    for m in members:
                        committee.add_member(m)
                else:
                    committee.add_member(members.text_content(), mtype.text)


    def scrape(self, chamber, term):
        base_url = 'http://www.ncga.state.nc.us/gascripts/Committees/Committees.asp?bPrintable=true&sAction=ViewCommitteeType&sActionDetails='

        chambers = {'upper': ['Senate%20Standing', 'Senate%20Select'],
                    'lower': ['House%20Standing', 'House%20Select']}

        for ctype in chambers[chamber]:
            with self.urlopen(base_url + ctype) as data:
                doc = lxml.html.fromstring(data)
                doc.make_links_absolute(base_url+ctype)
                for comm in doc.xpath('//ul/li/a'):
                    name = comm.text
                    url = comm.get('href')
                    committee = Committee(chamber, name)
                    self.scrape_committee(committee, url)
                    committee.add_source(url)
                    self.save_committee(committee)

