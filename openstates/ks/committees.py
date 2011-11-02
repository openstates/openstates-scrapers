import billy.scrape.committees

import lxml.html

committees_list_url = 'http://kslegislature.org/li/b2011_12/year1/committees/'

class KSCommitteeScraper(billy.scrape.committees.CommitteeScraper):
    state = 'ks'

    def scrape(self, chamber, time):
        with self.urlopen(committees_list_url) as committees_list_page:
            committees_list_page = lxml.html.fromstring(committees_list_page)

            commitee_main = committees_list_page.xpath("/html/body/div[@id='container']/div[@id='wrapper']/div[@id='main_content']")[0]

            if chamber == 'upper':
                table = commitee_main.xpath("div[@class='rightcol']")[0]
            else:
                table = commitee_main.xpath("div[@class='leftcol']")[0]

            committee_types = table.xpath('div')
            for committee_type in committee_types:
                type_title = committee_type.xpath('h3')[0].text_content()
                tabs = committee_type.xpath("div[@class='module']/ul")

                for tab in tabs:
                    rows = tab.xpath('li')
                    for row in rows:
                        href = row.xpath('a')[0].get('href')
                        title = row.xpath('a')[0].text_content()
                        self.scrape_committee(chamber, title, href)

    def scrape_committee(self, chamber, committee, committee_url):
        committee = billy.scrape.committees.Committee(chamber, committee)
        self.save_committee(committee)

