from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.sd import metadata

import html5lib


class SDLegislatorScraper(LegislatorScraper):
    state = 'sd'

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def _make_headers(self, url):
        # South Dakota's gzipped responses seem to be broken
        headers = super(SDLegislatorScraper, self)._make_headers(url)
        headers['Accept-Encoding'] = ''

        return headers

    def scrape(self, chamber, year):
        for session in metadata['sessions']:
            if session['start_year'] == int(year):
                break
        else:
            raise NoDataForPeriod(year)

        if int(year) >= 2009:
            self.scrape_new_legislators(chamber, year)
        else:
            self.scrape_old_legislators(chamber, year)

    def scrape_new_legislators(self, chamber, session):
        """
        Scrape legislators from 2009 and later.
        """

        if chamber == 'upper':
            search = 'Senate Members'
        else:
            search = 'House Members'

        leg_list_url = "http://legis.state.sd.us/sessions/%s/"\
            "MemberMenu.aspx" % (session)
        leg_list = self.soup_parser(self.urlopen(leg_list_url))

        list_div = leg_list.find(text=search).findNext('div')

        for link in list_div.findAll('a'):
            full_name = link.contents[0].strip()

            leg_page_url = "http://legis.state.sd.us/sessions/%s/%s" % (
                session, link['href'])
            leg_page = self.soup_parser(self.urlopen(leg_page_url))

            party = leg_page.find(
                id="ctl00_contentMain_spanParty").contents[0].strip()

            district = leg_page.find(
                id="ctl00_contentMain_spanDistrict").contents[0]
            district = district.strip().lstrip('0')

            occ_span = leg_page.find(id="ctl00_contentMain_spanOccupation")
            if len(occ_span.contents) > 0:
                occupation = occ_span.contents[0].strip()
            else:
                occupation = None

            legislator = Legislator(session, chamber, district,
                                    full_name, party=party,
                                    occupation=occupation)
            legislator.add_source(leg_page_url)
            self.save_legislator(legislator)

    def scrape_old_legislators(self, chamber, session):
        """
        Scrape pre-2009 legislators.
        """
        if chamber == 'upper':
            chamber_name = 'Senate'
        else:
            chamber_name = 'House'

        if int(session) < 2008:
            filename = 'district.htm'
        else:
            filename = 'MembersDistrict.htm'

        leg_list_url = "http://legis.state.sd.us/sessions/%s/%s" % (
            session, filename)
        leg_list = self.soup_parser(self.urlopen(leg_list_url))

        for district_str in leg_list.findAll('h2'):
            district = district_str.contents[0].split(' ')[1].lstrip('0')

            for row in district_str.findNext('table').findAll('tr')[1:]:
                if row.findAll('td')[1].contents[0].strip() != chamber_name:
                    continue

                full_name = row.td.a.contents[0].strip()

                party = row.findAll('td')[3].contents[0].strip()
                occupation = row.findAll('td')[4].contents[0].strip()

                legislator = Legislator(session, chamber, district,
                                        full_name, party=party,
                                        occupation=occupation)
                legislator.add_source(leg_list_url)
                self.save_legislator(legislator)
