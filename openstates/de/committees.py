import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee


class DECommitteeScraper(CommitteeScraper):
    jurisdiction = "de"

    def scrape(self, chamber, term):

        urls = {
            'upper': 'http://legis.delaware.gov/LIS/LIS%s.nsf/SCommittees',
            'lower': 'http://legis.delaware.gov/LIS/LIS%s.nsf/HCommittees'
        }

        # Mapping of term names to session numbers (see metatdata).
        term2session = {"2015-2016": "148", "2013-2014": "147",
                        "2011-2012": "146"}

        session = term2session[term]

        url = urls[chamber] % (session,)
        self.log(url)
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        committees = {}

        for row in page.xpath('//td[@width="96%"]/table/tr[@valign="top"]'):
            link = row.xpath('td/font/a[contains(@href, "opendocument")]')[0]
            committees[link.text] = link.attrib['href']
            self.log(link.attrib['href'])

        for c in committees:
            url = committees[c]
            page = lxml.html.fromstring(self.get(url).text)
            page.make_links_absolute(url)
            committee = Committee(chamber, c)
            committee.add_source(url)

            for tr in page.xpath('//td[@width="96%"]/table/tr'):
                role_section = tr.xpath('td/b/font')
                if(len(role_section) > 0):
                    role = re.sub(r's?:$', '', role_section[0].text).lower()
                    for member in tr.xpath('td/font/a'):
                        name = re.sub('\s+', ' ', member.text)
                        committee.add_member(name, role)

            self.save_committee(committee)
