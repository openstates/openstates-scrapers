import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .scraper import InvalidHTTPSScraper

import lxml.html


class IALegislatorScraper(InvalidHTTPSScraper, LegislatorScraper):
    jurisdiction = 'ia'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        session_id = self.metadata['session_details'][term]['number']

        if chamber == 'upper':
            chamber_name = 'senate'
        else:
            chamber_name = 'house'

        url = "https://www.legis.iowa.gov/legislators/%s" % chamber_name
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)
        table = page.xpath('//table[@id="sortableTable"]')[0]
        for link in table.xpath(".//a[contains(@href, 'legislator')]"):
            name = link.text.strip()
            leg_url = link.get('href')
            district = link.xpath("string(../../td[3])")
            party = link.xpath("string(../../td[4])")
            email = link.xpath("string(../../td[5])")

            if party == 'Democrat':
                party = 'Democratic'

            pid = re.search("personID=(\d+)", link.attrib['href']).group(1)
            photo_url = ("https://www.legis.iowa.gov/photo"
                         "?action=getPhoto&ga=%s&pid=%s" % (session_id, pid))

            leg = Legislator(term, chamber, district, name, party=party,
                             photo_url=photo_url, url=url)
            leg.add_source(url)

            leg_page = lxml.html.fromstring(self.get(link.attrib['href']).text)

            office_data = {
                "Legislative Email:": "email",
                "Home Phone:": "home_phone",
                "Home Address:": "home_addr",
                "Capitol Phone:": "office_phone",
            }
            metainf = {}

            table ,= leg_page.xpath(
                "//div[@class='legisIndent divideVert']/table"
            )
            for row in table.xpath(".//tr"):
                try:
                    key, value = (
                        x.text_content().strip() for x in row.xpath("./td")
                    )
                except ValueError:
                    continue

                try:
                    metainf[office_data[key]] = value
                except KeyError:
                    continue

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


            comm_path = "//a[contains(@href, 'committee?')]"
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
