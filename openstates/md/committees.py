import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

class MDCommitteeScraper(CommitteeScraper):

    jurisdiction = 'md'

    def scrape(self, term, chambers):
        # committee list
        url = 'http://mgaleg.maryland.gov/webmga/frmcommittees.aspx?pid=commpage&tab=subject7'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "cmtepage")]'):
            url = a.get('href').replace('stab=01', 'stab=04')
            chamber = a.xpath('../../..//th/text()')[0]
            if 'Senate' in chamber and 'upper' in chambers:
                chamber = 'upper'
                self.scrape_committee(chamber, a.text, url)
            elif 'House' in chamber and 'Delegation' not in chamber and 'lower' in chambers:
                chamber = 'lower'
                self.scrape_committee(chamber, a.text, url)
            elif chamber in ('Joint', 'Statutory', 'Special Joint'):
                chamber = 'joint'
                self.scrape_committee(chamber, a.text, url)


    def scrape_committee(self, chamber, com_name, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        com = Committee(chamber, com_name)
        com.add_source(url)

        for table in doc.xpath('//table[@class="grid"]'):
            rows = table.xpath('tr')
            sub_name = rows[0].getchildren()[0].text

            # new table - subcommittee
            if sub_name != 'Full Committee':
                com = Committee(chamber, com_name, subcommittee=sub_name)
                com.add_source(url)

            for row in rows[1:]:
                name = row.getchildren()[0].text_content()
                if name.endswith(' (Chair)'):
                    name = name.replace(' (Chair)','')
                    role = 'chair'
                elif name.endswith(' (Vice Chair)'):
                    name = name.replace(' (Vice Chair)','')
                    role = 'vice chair'
                elif name.endswith(' (Co-Chair)'):
                    name = name.replace(' (Co-Chair)','')
                    role = 'co-chair'
                else:
                    role = 'member'
                com.add_member(name, role)

            self.save_committee(com)
