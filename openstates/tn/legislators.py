from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

class TNLegislatorScraper(LegislatorScraper):
    state = 'tn'
    

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=False)
        root_url = 'http://www.capitol.tn.gov/'

        #testing for chamber
        if chamber == 'upper':
            url_chamber_name = 'senate'
            abbr = 's'
        else:
            url_chamber_name = 'house'
            abbr = 'h'
        if int(term) < 107:
            chamber_url = root_url + url_chamber_name + '/archives/'+term+'GA/Members/index.html'
        else:
            chamber_url = root_url + url_chamber_name + '/members/'

        with self.urlopen(chamber_url) as page:
            page = lxml.html.fromstring(page)

            for row in page.xpath("//tr")[1:]:
                party = row.xpath('td[2]')[0].text
                district = row.xpath('td[4]/a')[0].text.split()[1]
                phone = row.xpath('td[6]')[0].text
                email = row.xpath('td[7]/a')[0].text 
                member_url = root_url + url_chamber_name + '/members/' + abbr + district + '.html'
                
                with self.urlopen(member_url) as member_page:
                    member_page = lxml.html.fromstring(member_page)
                    name = member_page.xpath('//div[@id="membertitle"]/h2')[0].text
                    if 'Speaker' in name:
                        full_name = name[8:len(name)]
                    elif 'Lt.' in name:
                        full_name = name[13:len(name)]
                    elif abbr == 'h':
                        full_name = name[5: len(name)]
                    else:
                        full_name = name[8:len(name)]
                    
                    leg = Legislator(term, chamber, district, full_name, party=party, email=email)
                    leg.add_source(chamber_url)
                    leg.add_source(member_url)
                    self.save_legislator(leg)
