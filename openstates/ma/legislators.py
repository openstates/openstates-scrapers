import re

import lxml.html
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import (LegislatorScraper, Legislator,
                                            Person)

MAX_FETCH_ATTEMPTS = 3

found = {}
notFound = {}

class MALegislatorScraper(LegislatorScraper):
    state = 'ma'

    def scrape(self, chamber, term):
        if term != '187':
            # Data only available for current term
            raise NoDataForPeriod(term)

        for district in self.metadata['districts'][chamber]:
            found[district] = 0

        if chamber == 'upper':
            chamber_type = 'Senate'
        else:
            chamber_type = 'House'

        url = "http://www.malegislature.gov/People/%s" % (chamber_type,)
        with self.urlopen(url) as page:
            root = lxml.html.fromstring(page)

            for member_url in root.xpath('//div[@class="container"]/a/@href'):
                member_url = "http://www.malegislature.gov"+member_url
                self.scrape_member(chamber, term, member_url)

        print ''
        print 'Districts in web page, NOT FOUND in expected list:'
        for district in notFound:
            print district
            print ''
        print ''
        print 'District in expected list, NOT FOUND in web page:'
        for district in found:
            if found[district] == 0:
                print district
                print ''
        print ''

    def scrape_member(self, chamber, term, member_url):
        fetch_attempts = 0
        while True:
            with self.urlopen(member_url) as page:
                root = lxml.html.fromstring(page)

                if root.xpath('//title')[0].text.strip() != 'Error Occurred':
                    break

                fetch_attempts += 1

                self.log('Encountered error on "%s". Retrying.' % member_url)
                if fetch_attempts == MAX_FETCH_ATTEMPTS:
                    self.warning('Hit max fetch attempts for %s. Skipping.' % member_url)
                    return

        root.make_links_absolute(member_url)
        photo_url = root.xpath('//div[@class="bioPicContainer"]/img/@src')[0]
        full_name = root.xpath('//div[@class="bioPicContainer"]/img/@alt')[0]

        district = root.xpath('//div[@id="District"]//div[@class="widgetContent"]')
        if len(district):

            district = district[0].text.strip().upper()

            district = re.sub('\s+', ' ', district)

            district = re.sub(" AND ", " & ", district)

            district = re.sub('^TWENTY', 'TWENTY-', district)
            district = re.sub('^THIRTY', 'THIRTY-', district)
            district = re.sub('--', '-', district)

            if len(district.split(' - ')) > 1:
                district = district.split(' - ')[0]
            elif len(district.split('. ')) > 1:
                district = district.split('. ')[0]
            elif len(district.split(', CONSIST')) > 1:
                district = district.split(', CONSIST')[0]
            elif len(district.split(' CONSIST')) > 1:
                district = district.split(' CONSIST')[0]
            else:
                district = district[0:80]

            if len(district.split(' DISTRICT')) > 1:
                district = district.split(' DISTRICT')[0]

            district = re.sub('\.$', '', district)

            # Some special cases:

            district = re.sub('^DISTRICT REPRESENTED: ', '', district)
            district = re.sub('^16TH ', 'SIXTEENTH ', district)
            district = re.sub('^12TH', 'TWELFTH ', district)
            district = re.sub('^3RD ', 'THIRD ', district)
            district = re.sub('^6TH ', 'SIXTH ', district)
            district = re.sub('^8TH ', 'EIGHTH ', district)
            district = re.sub('^9TH ', 'NINTH ', district)

            if re.match('^NINTH NORFOLK DISTRCT', district): district = 'NINTH NORFOLK'

            if re.match('^FOURTEENTH WORCESTER', district): district = 'FOURTEENTH WORCESTER'

            # a double-space? Really?
            #
            if re.match('^TWELFTH  SUFFOLK ', district): district = 'TWELFTH SUFFOLK'

            # I tried to do a split on an m-dash that I found and I got an error when I ran the script.
            #
            # SyntaxError: Non-ASCII character '\xe2' in 
            #      file ./billy/bin/../../openstates/ma/legislators.py on line 79, but no encoding declared;
            #
            # For now, I will deal with this few cases manually.

            if re.match("^HAMPDEN ", district): district = 'HAMPDEN'

            if re.match("^CAPE & ISLANDS\.", district): district = 'CAPE & ISLANDS'

            # Some problems we are just not going to be able to fix

            if member_url == 'http://www.malegislature.gov/People/Profile/PVK1': district = 'FIRST HAMPSHIRE'

            if member_url == 'http://www.malegislature.gov/People/Profile/KNF1': district = 'FIRST WORCESTER'

            if member_url == 'http://www.malegislature.gov/People/Profile/E_C1': district = 'TENTH SUFFOLK'

            if district in self.metadata['districts'][chamber]:
                found[district] = 1
            else:
                print 'NO MATCH!'
                print district
                notFound[district] = 1
        else:
            district = 'NotFound'
        print ''

        party = root.xpath('//div[@class="bioDescription"]/div')[0].text.strip().split(',')[0]
        if party == 'Democrat':
            party = 'Democratic'
        elif party == 'Republican':
            party = 'Republican'

        leg = Legislator(term, chamber, district, full_name, party=party, photo_url=photo_url)

        leg.add_source(member_url)

        comm_div = root.xpath('//div[@id="Column5"]//div[@class="widgetContent"]')
        if len(comm_div):
            comm_div = comm_div[0]
            for li in comm_div.xpath('ul/li'):
                # Page shows no roll information for members.
                role = li.xpath('text()')[0].strip().strip(',') or 'member'
                comm = li.xpath('a/text()')[0]
                leg.add_role(role, term, chamber=chamber, committee=comm)

        self.save_legislator(leg)
