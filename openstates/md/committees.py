import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

class MDCommitteeScraper(CommitteeScraper):

    jurisdiction = 'md'

    def scrape(self, term, chamber):
        # committee list
        url = 'http://mgaleg.maryland.gov/webmga/frmcommittees.aspx?pid=commpage&tab=subject7'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "cmtepage")]'):
            url = a.get('href')
            chamber_name = a.xpath('../../..//th/text()')[0]
            if chamber_name == 'Senate Standing':
                url = url.replace('stab=01', 'stab=04')
            if chamber_name == 'House Standing':
                url = url.replace('stab=01', 'stab=04')
            com_name = a.text
            if com_name is None:
                continue
            com_name = com_name.replace("Joint ", "")
            com_name = com_name.replace("Committee on ", "")
            com_name = com_name.replace(" Committee", "")
            com_name = com_name.strip()
            if 'Senate' in chamber_name:
                chamber = 'upper'
            elif 'House' in chamber_name and 'Delegation' not in chamber_name:
                chamber = 'lower'
            elif 'Joint' or 'Statutory' or 'Special Joint' or 'Other' in chamber_name:
                chamber = 'joint'
            else:
                self.logger.warning("No committee chamber available for committee '%s'" % com_name)
                continue

            self.scrape_committee(chamber, com_name, url)

    def scrape_committee(self, chamber, com_name, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        com = Committee(chamber, com_name)
        com.add_source(url)

        for table in doc.xpath('//table[@class="grid"]'):
            rows = table.xpath('tr')
            sub_name = rows[0].getchildren()[0].text.strip()

            # new table - subcommittee
            if sub_name != 'Full Committee':
                com = Committee(chamber, com_name, subcommittee=sub_name)
                com.add_source(url)

            for row in rows[1:]:
                name = row.getchildren()[0].text_content().strip()
                if name.endswith(' (Chair)'):
                    name = name.replace(' (Chair)', '')
                    role = 'chair'
                elif name.endswith(' (Vice Chair)'):
                    name = name.replace(' (Vice Chair)', '')
                    role = 'vice chair'
                elif name.endswith(' (Co-Chair)'):
                    name = name.replace(' (Co-Chair)', '')
                    role = 'co-chair'
                else:
                    role = 'member'
                com.add_member(name, role)

        self.save_committee(com)
