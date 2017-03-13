from pupa.scrape import Scraper, Organization
import lxml.html

class IlCommitteeScraper(Scraper):

    def scrape_members(self, o, url):
        data = self.get(url).text
        if 'No members added' in data:
            return
        doc = lxml.html.fromstring(data)

        for row in doc.xpath('//table[@cellpadding="3"]/tr')[1:]:
            tds = row.xpath('td')

            # remove colon and lowercase role
            role = tds[0].text_content().replace(':','').strip().lower()

            name = tds[1].text_content().strip()
            o.add_member(name, role)


    def scrape(self):
        chambers = (('upper', 'senate'), ('lower', 'house'))
        for chamber, chamber_name in chambers:

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
                    o = Organization(name,
                                     classification='committee',
                                     chamber=chamber)

                else:
                    code = code.text_content().strip()


                    if 'Sub' in name:
                        o = Organization(name,
                                         classification='committee',
                                         parent_id={'name' : top_level_com})
                    else:
                        top_level_com = name
                        o = Organization(name,
                                         classification='committee',
                                         chamber=chamber)

                com_url = a.get('href')
                o.add_source(com_url)

                self.scrape_members(o, com_url)
                if o._related:
                    yield o
