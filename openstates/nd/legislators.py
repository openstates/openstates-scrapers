from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod
import lxml.html
import re

class NDLegislatorScraper(LegislatorScraper):
    state = 'nd'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        #testing for chamber
        if chamber == 'upper':
            url_chamber_name = 'senate'
        else:
            url_chamber_name = 'house'

        #figuring out starting year for url
        start_year = ((int(term) - 62)*2) + 2011
        root_url = 'http://www.legis.nd.gov/assembly/%s-%s/%s/' % (term, start_year, url_chamber_name)
        main_url = root_url + 'members/district.html'

        with self.urlopen(main_url) as page:
            page = lxml.html.fromstring(page)

            for member in page.xpath('//div[@class="content"][1]/table//tr/td[3]/a'):
                member_url = member.attrib['href'][3:len(member.attrib['href'])]

                #special case for Senator Ron Carlisle
                if 'sembly/' in member_url:
                    pos = member_url.index('senators')
                    member_url = member_url[pos:len(member_url)]
                
                if (('arloeschmidt' in member_url) or ('cbhaas' in member_url) or ('clarasueprice' in member_url)) and (term >= 62):
                    continue

                member_url = root_url + member_url
                with self.urlopen(member_url) as html:
                    leg_page = lxml.html.fromstring(html)
                    self.scrape_legislators(chamber, term, leg_page, member_url, main_url)

    def scrape_legislators(self, term, chamber, leg_page, member_url, main_url):
        full_name = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[1]/td/h2')[0].text
        if len(full_name.split()) == 3:
            first_name = full_name.split()[1]
            middle_name = ''
            last_name = full_name.split()[2]
            full_name = first_name + ' ' + last_name
        else:
            first_name = full_name.split()[1]
            middle_name = full_name.split()[2]
            last_name = full_name.split()[3]
            full_name = first_name + ' ' + middle_name + ' ' + last_name
        district = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[5]/td[2]')[0].text
        party = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[6]/td[2]')[0].text
        full_address = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[2]/td[2]')[0].text
        phone = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[3]/td[2]')[0].text
        email = leg_page.xpath('//div[@class="content"][1]/table[1]//tr[1]/td[2]/table//tr[4]/td[2]/a')[0].text
        
        if party == 'Democrat':
            party = 'Democratic'
        leg = Legislator(chamber, term, district, full_name, first_name, last_name, middle_name, party, full_address=full_address, phone=phone, email=email)
        leg.add_source(member_url)
        leg.add_source(main_url)
        self.save_legislator(leg)
