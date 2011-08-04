from billy.scrape.committees import CommitteeScraper, Committee 
import lxml.html
import re

class DECommitteeScraper(CommitteeScraper):
    state = "de"

    def scrape(self, chamber, term):
        urls = {
            'upper': 'http://legis.delaware.gov/LIS/LIS%s.nsf/SCommittees', 
            'lower': 'http://legis.delaware.gov/LIS/LIS%s.nsf/HCommittees'
        }
        url = urls[chamber] % (term,)
        self.log(url)
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        committees = {}

        for row in page.xpath('//td[@width="96%"]/table/tr[@valign="top"]'):
            link = row.xpath('td/font/a[contains(@href, "opendocument")]')[0]
            committees[link.text] = link.attrib['href']
            self.log(link.attrib['href'])

        for c in committees:
            url = committees[c]
            page = lxml.html.fromstring(self.urlopen(url))
            page.make_links_absolute(url)
            committee = Committee(chamber, c)
            committee.add_source(url)

            for tr in page.xpath('//td[@width="96%"]/table/tr'):
                role_section = tr.xpath('td/b/font')
                if(len(role_section) > 0):
                    role = re.sub(r's?:$','',role_section[0].text).lower()
                    for member in tr.xpath('td/font/a'):
                        committee.add_member(member.text, role)

            self.save_committee(committee)
