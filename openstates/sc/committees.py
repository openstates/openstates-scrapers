import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

class SCCommitteeScraper(CommitteeScraper):
    state = 'sc'

    def scrape(self, chamber, term):
        if chamber == 'lower':
            url = 'http://www.scstatehouse.gov/html-pages/housecommlst.html'
        else:
            url = 'http://www.scstatehouse.gov/html-pages/senatecommlst.html'

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            committees = doc.xpath('//span[@class="serifNormal" and '
                                   '@style="font-size: 17px; font-weight: bold;"]')
            for committee in committees:
                com = Committee(chamber, committee.text_content())
                com.add_source(url)

                member_table = committee.xpath('following-sibling::table')[0]
                for member in member_table.xpath('tr/td/span/a'):
                    name = member.text
                    roles = member.xpath('span')

                    if len(roles) == 0:
                        role = 'member'
                    else:
                        role = roles[0].text
                        name = name.rsplit(',', 1)[0]

                    com.add_member(name, role)

                self.save_committee(com)
