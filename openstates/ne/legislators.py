from billy.scrape.legislators import Legislator, LegislatorScraper
import lxml.html
import scrapelib

class NELegislatorScraper(LegislatorScraper):
    jurisdiction = 'ne'
    latest_only = True

    def scrape(self, term, chambers):
        base_url = 'http://news.legislature.ne.gov/dist'

        #there are 49 districts
        for district in range(1, 50):
            if district < 10:
                rep_url = base_url + '0' + str(district) + '/biography/'
            else:
                rep_url = base_url + str(district) + '/biography/'

            try:
                html = self.urlopen(rep_url)
                page = lxml.html.fromstring(html)

                full_name = page.xpath('//div[@class="content_header_right"]/a')[0].text.split(' ',1)[1].strip()
                # This is hacky, are lis always the same?
                address = page.xpath('//div[@id="sidebar"]/ul[1]/li[3]')[0].text.strip() + '\n'
                address += page.xpath('//div[@id="sidebar"]/ul[1]/li[4]')[0].text.strip() + '\n'
                address += page.xpath('//div[@id="sidebar"]/ul[1]/li[5]')[0].text.strip()
                phone = page.xpath('//div[@id="sidebar"]/ul[1]/li[6]')[0].text.split()
                if len(phone) > 2:
                    phone = phone[1] + ' ' + phone[2]
                else:
                    phone = None
                mailto = page.xpath('//div[@id="sidebar"]/ul[1]/li[contains(text(), "Email:")]/a/@href')[0]
                email = mailto[7:]

                photo_url = \
                        "http://www.nebraskalegislature.gov/media/images/blogs/dist%d02.jpg" \
                        % district

                #Nebraska is offically nonpartisan
                party = 'Nonpartisan'
                leg = Legislator(term, 'upper', str(district), full_name,
                                 party=party, email=email, url=rep_url,
                                 photo_url=photo_url)
                leg.add_source(rep_url)
                leg.add_office('capitol', 'Capitol Office', address=address,
                               phone=phone)
                self.save_legislator(leg)
            except scrapelib.HTTPError:
                self.warning('could not retrieve %s' % rep_url)

