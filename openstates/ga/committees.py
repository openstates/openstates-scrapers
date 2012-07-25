from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import scrapelib

class GACommitteeScraper(CommitteeScraper):
    state = 'ga'
    latest_only = True

    def scrape(self, term, chambers):
        self.joint_coms = {}
        for chamber in chambers:
            if chamber == 'upper':
                url = 'http://www.senate.ga.gov/committees/en-US/SenateCommitteesList.aspx'
            elif chamber == 'lower':
                url = 'http://www.house.ga.gov/committees/en-US/CommitteeList.aspx'

            self.scrape_chamber(url, chamber)

    def scrape_chamber(self, url, orig_chamber):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "committee.aspx")]'):
            com_name = a.text
            com_url = a.get('href')
            com_html = self.urlopen(com_url)
            com_data = lxml.html.fromstring(com_html)

            if 'Joint' in com_name:
                chamber = 'joint'
            else:
                chamber = orig_chamber

            if chamber == 'joint':
                if com_name not in self.joint_coms:
                    self.joint_coms[com_name] = Committee(chamber, com_name)
                com = self.joint_coms.get(com_name)
                self.joint_coms[com_name] = com
            else:
                com = Committee(chamber, com_name)

            for a in com_data.xpath('//a[contains(@href, "Member=")]'):
                member = a.text
                role = a.xpath('../following-sibling::span/text()')
                if role:
                    role = role[0].lower().replace(u'\xa0', ' ')
                    # skip former members
                    if 'until' in role:
                        continue
                else:
                    role = 'member'
                com.add_member(member, role)

            com.add_source(com_url)
            self.save_committee(com)
