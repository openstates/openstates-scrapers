import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class IALegislatorScraper(LegislatorScraper):
    jurisdiction = 'ia'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            chamber_name = 'senate'
        else:
            chamber_name = 'house'

        url = "http://www.legis.iowa.gov/Legislators/%s.aspx" % chamber_name
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)
        table = page.xpath('//table[@class="legis"]')[0]
        for link in table.xpath(".//a[contains(@href, 'legislator.aspx')]"):
            name = link.text.strip()
            leg_url = link.get('href')
            district = link.xpath("string(../../td[2])")
            party = link.xpath("string(../../td[3])")
            email = link.xpath("string(../../td[5])")

            if party == 'Democrat':
                party = 'Democratic'

            pid = re.search("PID=(\d+)", link.attrib['href']).group(1)
            photo_url = ("http://www.legis.iowa.gov/getPhotoPeople.aspx"
                         "?GA=84&PID=%s" % pid)

            leg = Legislator(term, chamber, district, name, party=party,
                             email=email, photo_url=photo_url, url=url)
            leg.add_source(url)

            leg_page = lxml.html.fromstring(self.urlopen(link.attrib['href']))

            office_data = {
                "email": "ctl00_cphMainContent_divEmailLegis",
                "home_phone": "ctl00_cphMainContent_divPhoneHome",
                "home_addr": "ctl00_cphMainContent_divAddrHome",
                "office_phone": "ctl00_cphMainContent_divPhoneCapitol",
            }
            metainf = {}

            for attr in office_data:
                path = office_data[attr]
                info = leg_page.xpath("//div[@id='%s']" % path)
                if len(info) != 1:
                    continue
                info = info[0]

                _, data = [x.text_content() for x in info.xpath("./span")]
                data = data.strip()
                if data == "":
                    continue

                metainf[attr] = data

            if "home_phone" in metainf or "home_addr" in metainf:
                home_args = {}
                if "home_phone" in metainf:
                    home_args['phone'] = metainf['home_phone']
                if "home_addr" in metainf:
                    home_args['address'] = metainf['home_addr']
                leg.add_office('district',
                               'Home Office',
                               **home_args)

            if "email" in metainf or "office_phone" in metainf:
                cap_args = {}

                if "email" in metainf:
                    cap_args['email'] = metainf['email']
                if "office_phone" in metainf:
                    cap_args['phone'] = metainf['office_phone']

                leg.add_office('capitol',
                               'Capitol Office',
                               **cap_args)


            comm_path = "//a[contains(@href, 'committee')]"
            for comm_link in leg_page.xpath(comm_path):
                comm = comm_link.text.strip()

                match = re.search(r'\((.+)\)$', comm)
                if match:
                    comm = re.sub(r'\((.+)\)$', '', comm).strip()
                    mtype = match.group(1).lower()
                else:
                    mtype = 'member'

                if comm.endswith('Appropriations Subcommittee'):
                    sub = re.match('^(.+) Appropriations Subcommittee$',
                                   comm).group(1)
                    leg.add_role('committee member', term, chamber=chamber,
                                 committee='Appropriations',
                                 subcommittee=sub,
                                 position=mtype)
                else:
                    leg.add_role('committee member', term, chamber=chamber,
                                 committee=comm,
                                 position=mtype)

            self.save_legislator(leg)
