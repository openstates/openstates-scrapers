import billy.scrape.legislators

import lxml.html
import re

legislator_list_url = 'http://kslegislature.org/li/b2011_12/year1/members/'
legislator_name_pattern = re.compile('(Representative|Senator) ([A-Za-z]+) ([A-Za-z]+)')
legislator_line_pattern = re.compile('Party: ([A-Za-z]+)       First Term: ([0-9]+)')

class KSLegislatorScraper(billy.scrape.legislators.LegislatorScraper):
    state = 'ks'

    def scrape(self, chamber, term):
        with self.urlopen(legislator_list_url) as legislator_list_page:
            legislator_list_page = lxml.html.fromstring(legislator_list_page)

            legislator_main = legislator_list_page.xpath("/html/body/div[@id='container']/div[@id='wrapper']/div[@id='main_content']/div[@id='main']")

            self.debug(legislator_main)
            if chamber == 'upper':
                table = legislator_main[0].xpath('div')[1]
            else:
                table = legislator_main[0].xpath('div')[0]

            tabs = table.xpath("div[@class='module']/ul")
            for tab in tabs:
                rows = tab.xpath('li')
                for row in rows:
                    name = row.xpath('a')[0].text_content()
                    url = row.xpath('a').get('href')
                    self.scrape_legislator(chamber, term, name, url)

    def scrape_legislator(self, chamber, term, name, url):
        with self.urlopen(url) as legislator_page:
            legislator_page = lxml.html.fromstring(legislator_page)

            main = legislator_page.xpath("/html/body/div[@id='container']/div[@id='wrapper']/div[@id='main_content']/div[@id='main']")
            name = main.xpath('h1').text_content()
            district = main.xpath('h2').text_content()
            info = main.xpath('h3').text_content()

            match = legislator_name_pattern.match(name)
            if match:
                first_name = match.group(2)
                last_name = match.group(3)
            
                match = legislator_line_pattern.match(info)
                if match:
                    party = match.group(1)

                    legislator = billy.scrape.legislators.Legislator(term, chamber, district, "%s %s" % (first_name, last_name), first_name, last_name, '', party)
                    legislator.add_source(url)

                    self.save_legislator(legislator)

