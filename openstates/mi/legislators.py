import re

from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

abbr = {'D': 'Democratic', 'R': 'Republican'}

class MILegislatorScraper(LegislatorScraper):
    jurisdiction = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        if chamber == 'lower':
            return self.scrape_lower(chamber, term)
        return self.scrape_upper(chamber, term)

    def scrape_lower(self, chamber, term):
        url = 'http://www.house.mi.gov/mhrpublic/frmRepList.aspx'
        table = [
            "website",
            "district",
            "name",
            "party",
            "location",
            "phone",
            "email"
        ]
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        # skip two rows at top
        for row in doc.xpath('//table[@id="grvRepInfo"]/*'):
            tds = row.xpath('.//td')
            if len(tds) == 0:
                continue
            metainf = {}
            for i in range(0, len(table)):
                metainf[table[i]] = tds[i]
            district = str(int(metainf['district'].text_content().strip()))
            party = metainf['party'].text_content().strip()
            office = metainf['location'].text_content().strip()
            phone = metainf['phone'].text_content().strip()
            email = metainf['email'].text_content().strip()
            leg_url = metainf['website'].xpath("./a")[0].attrib['href']
            name = metainf['name'].text_content().strip()
            if name == 'Vacant':
                self.info('district %s is vacant', district)
                continue
            leg = Legislator(term=term,
                             chamber=chamber,
                             full_name=name,
                             district=district,
                             party=abbr[party],
                             url=leg_url)

            leg.add_office('capitol', 'Capitol Office',
                           address=office,
                           phone=phone,
                           email=email)

            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_upper(self, chamber, term):
        url = 'http://www.senate.michigan.gov/members/memberlist.htm'
        r_contact_url_pattern = 'http://www.misenategop.com/senators/contact.asp?District=%s'

        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        for row in doc.xpath('//table[@width=550]/tr')[1:39]:
            # party, dist, member, office_phone, office_fax, office_loc
            party, dist, member, phone, fax, loc = row.getchildren()
            party = abbr[party.text]
            district = dist.text_content().strip()
            name = member.text_content().strip()
            if name == 'Vacant':
                self.info('district %s is vacant', district)
                continue
            leg_url = member.xpath('a/@href')[0]
            office_phone = phone.text
            office_fax = fax.text
            office_loc = loc.text

            email = None
            if party == abbr['R']:
                contact_url = r_contact_url_pattern % district
                contact_html = self.urlopen(contact_url)
                contact_doc = lxml.html.fromstring(contact_html)
                email_link = contact_doc.xpath(".//*[@id='yui-main']/div/div/table/tr[9]/td[2]/p/a")
                if(email_link):
                    email_link_attr = email_link[0].attrib['href']
                    if email_link_attr[0:7] == 'mailto:':
                        email = email_link_attr[7:]


            leg = Legislator(term=term, chamber=chamber,
                             district=district,
                             full_name=name,
                             party=party,
                             url=leg_url)

            leg.add_office('capitol', 'Capitol Office',
                           address=office_loc,
                           fax=office_fax,
                           phone=office_phone,
                           email=email)


            if email:
                leg.add_source(contact_url)

            leg.add_source(url)
            self.save_legislator(leg)
