from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import scrapelib

class GACommitteeScraper(CommitteeScraper):
    state = 'ga'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            url = 'http://www.senate.ga.gov/committees/en-US/SenateCommitteesList.aspx'
            self.scrape_senate(url)
        else:
            year = int(term[0: term.index('-')])
            session = "%s_%s" % (year, str(year + 1)[-2:])
            url = 'http://www1.legis.ga.gov/legis/%s/house/commroster.htm' % session

            self.scrape_house(url)

    def scrape_senate(self, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "committee.aspx")]'):
            com_name = a.text
            com_url = a.get('href')
            com_html = self.urlopen(com_url)
            com_data = lxml.html.fromstring(com_html)

            com = Committee('upper', com_name)

            for span in com_data.xpath('//span[@style="float:left; width:45%;"]'):
                member = span.xpath('a/text()')[0]
                role = span.xpath('following-sibling::span/text()')[0].lower()
                com.add_member(member, role)

            com.add_source(com_url)
            self.save_committee(com)


    def scrape_house(self, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(url)
        doc.make_links_absolute(url)

        for a in doc.xpath('//td/a'):
            com_name = a.text.strip()
            # blank entries in table
            if not com_name:
                continue
            com_url = a.get('href')
            com_html = self.urlopen(com_url)
            com_data = lxml.html.fromstring(com_html)

            com = Committee('lower', com_name)

            for td in doc.xpath('//table[@id="commtable"]')[1].xpath('.//td'):
                leg = td.xpath('.//a/text()')
                if leg:
                    leg = leg[0]
                    pieces = td.text_content().split('\n')
                    if len(pieces) == 2:
                        role = pieces[1].lower()
                    else:
                        role = 'member'
                    com.add_member(leg, role)

            com.add_source(com_url)
            self.save_committee(com)

