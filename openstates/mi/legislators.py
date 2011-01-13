import re

from billy.scrape.legislators import LegislatorScraper, Legislator

from BeautifulSoup import BeautifulSoup

class MILegislatorScraper(LegislatorScraper):
    state = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        abbr = {'D': 'Democratic', 'R': 'Republican'}

        if chamber == 'lower':
            with self.urlopen('http://house.michigan.gov/replist.asp') as html:
                legs = BeautifulSoup(html)
                for leg in legs.findAll('table', text='First Name'):
                    for tr in leg.parent.parent.parent.parent.parent.findAll('tr'):  #a - font - th - tr - table
                        if tr.findAll('th') != []: continue
                        (district, last_name, first_name, party) = tr.findAll('td', limit=4)
                        if last_name.div.a.font.string is None: continue
                        if party.div.font.string.strip() == '': continue
                        last_name = last_name.div.a.font.string.strip()
                        first_name = first_name.div.a.font.string.strip()
                        district = district.div.font.string.strip()
                        party = abbr[party.div.font.string.strip()]
                        leg = Legislator(term, chamber, district,
                                         first_name + " " + last_name,
                                         first_name, last_name,
                                         party=party)
                        self.save_legislator(leg)
        else:
            with self.urlopen('http://www.senate.michigan.gov/SenatorInfo/alphabetical_list_of_senators.htm') as html:
                legs = BeautifulSoup(html)
                for tr in legs.findAll('tr'):
                    tds = tr.findAll('td', limit=4)
                    if len(tds) != 4: continue
                    (name, hometown , district, party) = tds
                    if name.font is None or name.font.a is None: continue
                    #if district.string is None: continue
                    name = name.font.a.string.strip().replace('\n','')
                    whitespace = re.compile('\s+')
                    name = whitespace.sub(' ', name)
                    name = name.split(', ')
                    name = "%s %s" % (name[1], name[0]) #.reverse() didn't work and I didn't care
                    if district.p: district = district.p.a.font.string.strip()
                    elif district.a: district = district.a.font.string.strip()
                    else: continue 

                    party = party.font.string.strip()
                    leg = Legislator(term, chamber, district, name, party=party)
                    self.save_legislator(leg)
