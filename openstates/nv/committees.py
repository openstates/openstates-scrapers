import re
import datetime

from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class NVCommitteeScraper(CommitteeScraper):
    state = 'nv'

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

        chamber_letter = {'lower':'A', 'upper':'S'}[chamber]

        url = 'http://www.leg.state.nv.us/Session/%s/Committees/%s_Committees/' % (
            insert, chamber_letter)

        with self.urlopen(url) as page:
            root = lxml.html.fromstring(page)
            for com_a in root.xpath('//strong/a'):
                com_url = url + com_a.get('href')
                com = Committee(chamber, com_a.text)
                com.add_source(com_url)
                self.scrape_comm_members(chamber, com, com_url)
                self.save_committee(com)

    def scrape_comm_members(self, chamber, committee, url):
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            for name in doc.xpath('//li/a/text()'):
                committee.add_member(name.strip())
