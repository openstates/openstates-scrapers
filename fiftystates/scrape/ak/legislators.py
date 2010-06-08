import re
import datetime as dt

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import html5lib


class AKLegislatorScraper(LegislatorScraper):
    state = 'ak'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape(self, chamber, year):
        # Data available for 1993 on
        if int(year) < 1993 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        if chamber == 'upper':
            chamber_abbr = 'S'
        else:
            chamber_abbr = 'H'

        session = str(18 + ((int(year) - 1993) / 2))

        leg_list_url = "http://www.legis.state.ak.us/"\
            "basis/commbr_info.asp?session=%s" % session
        leg_list = self.soup_parser(self.urlopen(leg_list_url))

        leg_re = "get_mbr_info.asp\?member=.+&house=%s&session=%s" % (
            chamber_abbr, session)
        links = leg_list.findAll(href=re.compile(leg_re))

        for link in links:
            member_url = "http://www.legis.state.ak.us/basis/" + link['href']
            member_page = self.soup_parser(self.urlopen(member_url))

            if member_page.find('td', text=re.compile('Resigned')):
                # Need a better way to handle this than just dropping
                continue

            full_name = member_page.findAll('h3')[1].contents[0]
            full_name = ' '.join(full_name.split(' ')[1:])
            full_name = re.sub('\s+', ' ', full_name).strip()

            first_name = full_name.split(' ')[0]
            last_name = full_name.split(' ')[-1]
            middle_name = ' '.join(full_name.split(' ')[1:-1])

            code = link['href'][24:27]

            district = member_page.find(text=re.compile("District:"))
            district = district.strip().split(' ')[-1]

            party = member_page.find(text=re.compile("Party: "))
            party = ' '.join(party.split(' ')[1:])

            leg = Legislator(session, chamber, district,
                             full_name, first_name,
                             last_name, middle_name,
                             party, code=code)
            leg.add_source(member_url)
            self.save_legislator(leg)
