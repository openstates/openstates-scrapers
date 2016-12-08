from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class NCCommitteeScraper(CommitteeScraper):
    jurisdiction = 'nc'

    def scrape_committee(self, committee, url):
        url = url.replace(' ', '%20') + '&bPrintable=true'
        data = self.get(url).text
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
                data = self.get(base_url + ctype).text
                doc = lxml.html.fromstring(data)
                doc.make_links_absolute(base_url+ctype)
                for comm in doc.xpath('//ul/li/a'):
                    name = comm.text
                    # skip committee of whole Senate
                    if 'Whole Senate' in name:
                        continue
                    url = comm.get('href')
                    committee = Committee(chamber, name)
                    self.scrape_committee(committee, url)
                    committee.add_source(url)
                    if not committee['members']:
                        self.warning('empty committee: %s', name)
                    else:
                        self.save_committee(committee)

