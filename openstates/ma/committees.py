
from billy.scrape.committees import CommitteeScraper, Committee

from BeautifulSoup import BeautifulSoup

import re

class MACommitteeScraper(CommitteeScraper):
    state = 'ma'

    def scrape(self, chamber, term):
        pageTypes = {}

        if chamber == 'upper':
            pageTypes['Senate'] = 1
            pageTypes['Joint'] = 1

        if chamber == 'lower':
            pageTypes['House'] = 1

        foundComms = []

        for pageType in pageTypes:
            url = 'http://www.malegislature.gov/Committees/' + pageType

            page = self.urlopen(url);
            soup = BeautifulSoup(page)

            links = soup.findAll('a', href=re.compile("^/"))

            for link in links:
                c1 = (link['href'] == '/Budget/HouseBudget')
                c2 = (link['href'] == '/Committees/SenateWaysAndMeans')
                c3 = (link['href'] == '/Committees/HouseWaysAndMeans')
                c4 = (re.match('^/Committees/Senate/', link['href']))
                c5 = (re.match('^/Committees/House/', link['href']))
                c6 = (re.match('^/Committees/Joint/', link['href']))

                if c1 or c2 or c3 or c4 or c5 or c6:
                    thisComm = {}
                    thisComm['href'] = link['href']
                    thisComm['name'] = link.string
                    foundComms.append(thisComm)

        for commInfo in foundComms:
            # print commInfo
            page = self.urlopen('http://www.malegislature.gov' + commInfo['href'])

            if re.search('House', commInfo['href']): thisChamber = 'lower'
            if re.search('Senate', commInfo['href']): thisChamber = 'upper'
            if re.search('Joint', commInfo['href']): thisChamber = 'joint'

            soup = BeautifulSoup(page)
            commRoles = soup.findAll('div', { 'class' : 'describe' })

            if len(commRoles) > 0:

                foundRoles = []

                for commRole in commRoles:

                    bolded = commRole.findNext('b')
                    linked = commRole.findNext('a')

                    foundRole = {}

                    if len(bolded) == 1:
                        foundRole['role'] = bolded.string
                    if len(bolded) > 1:
                        foundRole['role'] = bolded.contents[0] + ' ' + bolded.contents[2]
                    if linked.string is not None:
                        foundRole['name'] = linked.string

                    if 'role' not in foundRole:
                        foundRole['role'] = 'UNKNOWN'

                    foundRoles.append(foundRole)

                commMembers = soup.findAll('div', { 'class' : 'membersGallyList' })

                foundMembers = commMembers[0].findAll('a')

                for foundMember in foundMembers:
                    foundRole = {}
                    foundRole['role'] = 'member'
                    foundRole['name'] = foundMember.string
                    foundRoles.append(foundRole)

                nextComm = Committee(thisChamber, commInfo['name'])

                nextComm.add_source('http://www.malegislature.gov' + commInfo['href'])

                for member in foundRoles:
                    nextComm.add_member(member['name'], member['role'])

                self.save_committee(nextComm)

