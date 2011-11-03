from billy.scrape.legislators import Legislator, LegislatorScraper
import lxml.html
import scrapelib

class NELegislatorScraper(LegislatorScraper):
    state = 'ne'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        base_url = 'http://news.legislature.ne.gov/dist'

        if chamber == 'lower':
            raise Exception('Nebraska is unicameral. Call again with upper')

        #there are 49 districts
        for district in range(1, 50):
            if district < 10:
                rep_url = base_url + '0' + str(district) + '/biography/'
            else:
                rep_url = base_url + str(district) + '/biography/'

            try:
                html = self.urlopen(rep_url)
                page = lxml.html.fromstring(html)

                full_name = page.xpath('//div[@class="content_header_right"]/a')[0].text.split()
                first_name = full_name[1]
                last_name = full_name[2]

                email = page.xpath('//div[@id="sidebar"]/ul[1]/li[7]/a')[0].text or ''
                phone = page.xpath('//div[@id="sidebar"]/ul[1]/li[6]')[0].text.split()
                phone = phone[1] + '-' + phone[2]

                #Nebraska is offically nonpartisan
                party = 'Nonpartisan'
                middle_name = ''
                leg = Legislator(term, chamber, str(district), first_name + ' ' + last_name,
                first_name, last_name, middle_name, party, email=email, phone=phone)
                leg.add_source(rep_url)
                self.save_legislator(leg)
            except scrapelib.HTTPError:
                self.warning('could not retrieve %s' % rep_url)

