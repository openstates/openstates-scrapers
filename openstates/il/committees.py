from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class ILCommitteeScraper(CommitteeScraper):
    jurisdiction = 'il'

    def scrape_members(self, com, url):
        data = self.get(url).text
        if 'No members added' in data:
            return
        doc = lxml.html.fromstring(data)

        for row in doc.xpath('//table[@cellpadding="3"]/tr')[1:]:
            tds = row.xpath('td')

            # remove colon and lowercase role
            role = tds[0].text_content().replace(':','').strip().lower()

            name = tds[1].text_content().strip()
            com.add_member(name, role)


    def scrape(self, chamber, term):
        chamber_name = 'senate' if chamber == 'upper' else 'house'

        url = 'http://ilga.gov/{0}/committees/default.asp'.format(chamber_name)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        top_level_com = None

        for a in doc.xpath('//a[contains(@href, "members.asp")]'):
            name = a.text.strip()
            code = a.getparent().getnext()
            if code is None:
                #committee doesn't have a code, maybe it's a taskforce?
                com = Committee(chamber, name)

            else:
                code = code.text_content().strip()

                if 'Sub' in name:
                    com = Committee(chamber, top_level_com, name, code=code)
                else:
                    top_level_com = name
                    com = Committee(chamber, name, code=code)

            com_url = a.get('href')
            self.scrape_members(com, com_url)
            com.add_source(com_url)
            if not com['members']:
                self.log('skipping empty committee on {0}'.format(com_url))
            else:
                self.save_committee(com)
