import lxml.html

from pupa.scrape import Organization, Scraper


def clean_name(com_name):
    if com_name.startswith("Joint "):
        com_name = com_name.replace("Joint ", "", 1)
    com_name = com_name.replace("Special Committee on ", "")
    com_name = com_name.replace("Committee on ", "")
    if com_name.endswith("Committee"):
        com_name = com_name.replace(" Committee", "")
    com_name = com_name.strip()
    if com_name.startswith('the'):
        com_name = com_name.replace('the', 'The')
    return com_name


def define_role(name):
    if name.endswith(' (House Chair)'):
        name = name.replace(' (House Chair)', '')
        role = 'house chair'
    elif name.endswith(' (Senate Chair)'):
        name = name.replace(' (Senate Chair)', '')
        role = 'senate chair'
    elif name.endswith(' (Chair)'):
        name = name.replace(' (Chair)', '')
        role = 'chair'
    elif name.endswith(' (Senate Vice Chair)'):
        name = name.replace(' (Senate Vice Chair)', '')
        role = 'vice chair'
    elif name.endswith(' (Senate Co-Chair)'):
        name = name.replace(' (Senate Co-Chair)', '')
        role = 'co-chair'
    elif name.endswith(' (House Vice Chair)'):
        name = name.replace(' (House Vice Chair)', '')
        role = 'vice chair'
    elif name.endswith(' (House Co-Chair)'):
        name = name.replace(' (House Co-Chair)', '')
        role = 'co-chair'
    elif name.startswith('House Chair:'):
        name = name.replace('House Chair:', '')
        role = 'house chair'
    elif name.startswith('Senate Chair:'):
        name = name.replace('Senate Chair:', '')
        role = 'senate chair'
    elif name.endswith(' (Vice Chair)'):
        name = name.replace(' (Vice Chair)', '')
        role = 'vice chair'
    elif name.endswith(' (Co-Chair)'):
        name = name.replace(' (Co-Chair)', '')
        role = 'co-chair'
    else:
        role = 'member'
    if name.startswith("Delegate "):
        name = name.replace("Delegate", "", 1).strip()
    if name.startswith("Senator "):
        name = name.replace("Senator", "", 1).strip()
    if name.count(', ') == 1:
        name = ' '.join(name.split(', ')[::-1])
    return (name, role)


class MDCommitteeScraper(Scraper):
    def scrape(self):
        url = 'http://mgaleg.maryland.gov/webmga/frmcommittees.aspx?pid=commpage&tab=subject7'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        self.parents = {}

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

            com_name = clean_name(com_name)

            if 'Senate' in chamber_name:
                chamber = 'upper'
            elif 'House' in chamber_name:
                chamber = 'lower'
            elif 'Joint' in chamber_name:
                chamber = 'legislature'
            elif 'Statutory' in chamber_name:
                chamber = 'legislature'
            elif 'Special Joint' in chamber_name:
                chamber = 'legislature'
            elif 'Other' in chamber_name:
                chamber = 'legislature'
            else:
                self.logger.warning("No committee chamber available for committee '%s'" % com_name)
                continue

            com = self.scrape_committee(chamber, com_name, url)
            self.parents[(chamber, com_name)] = com._id
            yield com

        for a in doc.xpath('//a[contains(@href, "AELR")]'):
            url = a.get('href')
            chamber_name = a.xpath('../../..//th/text()')[0]
            chamber = 'legislature'
            com_name = a.text
            if com_name is None:
                continue
            com_name = clean_name(com_name)

            com = self.scrape_committee(chamber, com_name, url)
            self.parents[(chamber, com_name)] = com._id
            yield com

    def scrape_committee(self, chamber, com_name, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        com = Organization(chamber=chamber, name=com_name, classification='committee')
        com.add_source(url)

        if 'stab=04' in url:
            for table in doc.xpath('//table[@class="grid"]'):
                rows = table.xpath('tr')
                sub_name = rows[0].getchildren()[0].text.strip()

                # new table - subcommittee
                if sub_name != 'Full Committee':
                    sub_name = sub_name.replace("Subcommittee", "").strip()
                    com = Organization(
                        name=sub_name, classification='committee',
                        parent_id=self.parents[(chamber, com_name)])
                    com.add_source(url)

                for row in rows[1:]:
                    name = row.getchildren()[0].text_content().strip()
                    name, role = define_role(name)
                    com.add_member(name, role)

                return com
        else:
            table_source = doc.xpath('//table[@class="noncogrid"]')

            if table_source != []:
                for table in table_source:
                    row = table.xpath('tr/td/a[contains(@href, "sponpage")]/text()')
                    sub_name_source = table.xpath('tr/th/text()')

                    if "Subcommittee" in sub_name_source[0]:
                        sub_name = sub_name_source[0]
                        sub_name = sub_name.replace("Subcommittee", "").strip()
                        com = Organization(
                            name=sub_name, classification='committee',
                            parent_id=self.parents[(chamber, com_name)])
                        com.add_source(url)

                    for name in row:
                        name, role = define_role(name)
                        com.add_member(name, role)

                    return com
            else:
                row = doc.xpath('//table[@class="spco"]/tr[1]/td/text()')
                for name in row:
                    name, role = define_role(name)
                    com.add_member(name, role)

                return com
