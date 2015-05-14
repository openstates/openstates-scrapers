import re

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

nelis_root = 'https://www.leg.state.nv.us/App/NELIS/REL'


class NVCommitteeScraper(CommitteeScraper):
    jurisdiction = 'nv'

    def scrape(self, chamber, term):

        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'
        insert = str(session) + sessionsuffix + str(term[0:4])

        chamber_names = {'lower': 'Assembly', 'upper': 'Senate'}

        insert = self.metadata['session_details'][session].get(
            '_committee_session', insert
        )

        list_url = '%s/%s/HomeCommittee/LoadCommitteeListTab' % (nelis_root, insert)
        html = self.get(list_url).text
        doc = lxml.html.fromstring(html)

        sel = 'panel%sCommittees' % chamber_names[chamber]

        ul = doc.xpath('//ul[@id="%s"]' % sel)[0]
        coms = ul.xpath('li/div/div/div[@class="col-md-4"]/a')

        for com in coms:
            name = com.text.strip()
            com_id = re.match(r'.*/Committee/(?P<id>[0-9]+)/Overview', com.attrib['href']).group('id')
            com_url = '%s/%s/Committee/FillSelectedCommitteeTab?committeeOrSubCommitteeKey=%s&selectedTab=Overview' % (nelis_root, insert, com_id)
            com = Committee(chamber, name)
            com.add_source(com_url)
            self.scrape_comm_members(chamber, com, com_url)
            self.save_committee(com)

    def scrape_comm_members(self, chamber, committee, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        links = doc.xpath('//div[@class="col-md-11"]/a[@class="bio"]')
        for link in links:
            name = link.text.strip()
            role = link.tail.strip().replace("- ", "")
            if role == '':
                role = 'member'
            committee.add_member(name, role)
