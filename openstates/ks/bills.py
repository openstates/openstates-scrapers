import billy.scrape.bills

import datetime
import re
import lxml.html

bill_title_pattern = re.compile('([HS]B[0-9]+) - (.*)')
bill_status_pattern = re.compile('Approved by (.*) on .*')

domain = 'http://www.kslegislature.org'
bills_list_url = domain + '/li/b%s/%s/measures/%s/'

class KSBillScraper(billy.scrape.bills.BillScraper):
    state = 'ks'

    def scrape(self, chamber, session):
        if datetime.date.today().year - int(session) < 2:
            self.scrape_current(chamber, session)
        #else:
        #    self.scrape_archive(chamber, session)

    #def scrape_archive(self, chamber, session):

    def scrape_current_bill(self, chamber, session, bill_id, title, href):
        bill = billy.scrape.bills.Bill(session, chamber, bill_id, title)
        with self.urlopen(href) as bill_page:
            bill_page = lxml.html.fromstring(bill_page)

            bill.add_source(href)

            main_content = bill_page.xpath("/html/body/div[@id='container']/div[@id='wrapper']/div[@id='main_content']")

            bill_sponsor_tabs = main_content[0].xpath("div[@id='sidebar']/div[1]/div[@class='portlet-content']/span[@class='tab-group']/div[@class='infinite-tabs']/ul")
            for tab in bill_sponsor_tabs:
                rows = tab.xpath('li')
                for row in rows:
                    sponsor = item.xpath('a').text_content()
                    if sponsor:
                        bill.add_sponsor('primary', sponsor)

            bill_version_tabs = main_content[0].xpath("div[@id='main']/div[@class='tabs']/div[@class='module']/table/tbody")
            for tab in bill_version_tabs:
                rows = tab.xpath('tr')
                for row in tab.xpath('tr'):
                    name = row.xpath('td')[0].text_content()
                    try:
                        href = row.xpath('td')[1].xpath("a[@class='pdf']/@href")[0]
                        bill.add_version(name, href)
                    except(IndexError):
                        continue

            bill_history_tabs = main_content[0].xpath("div[@id='full']/div[@class='tabs']/div[@class='module']/table/tbody")
            for tab in bill_history_tabs:
                rows = tab.xpath('tr')
                for row in rows:
                    date = row.xpath('td[1]')[0].text_content()
                    chamber = row.xpath('td[2]')[0].text_content()
                    status = row.xpath('td[3]')[0]
                    match = bill_status_pattern.match(status.text_content())
                    if match:
                        bill.add_action(match.group(1), status.text_content(), datetime.datetime.strptime(date, '%a %d %b %Y'))
                    elif status.xpath('a'):
                        objects = status.xpath('a')
                        bill.add_action(objects[0].text_content(), status.text_content(), datetime.datetime.strptime(date, '%a %d %b %Y'))
                    else:
                        bill.add_action(chamber, status.text_content(), datetime.datetime.strptime(date, '%a %d %b %Y'))

                    ar = row.xpath("td[4]/a[@class='pdf']")
                    if ar:
                        bill.add_document(status.text_content(), ar[0].get('href'))
        self.save_bill(bill)

    def scrape_current(self, chamber, session):
        session_year = int(session)
        if session_year % 2 == 1:
            year = 'year1'
            year_pair = '%i_%i' % (session_year, session_year + 1 - 2000)
        else:
            year = 'year2'
            year_pair = '%i_%i' % (session_year - 1, session_year - 2000)

        index_url = bills_list_url % (year_pair, year, 'senate' if chamber == 'upper' else 'house')
        with self.urlopen(index_url) as index_page:
            index_page = lxml.html.fromstring(index_page)

            bill_tabs = index_page.xpath("//div[@id='main']/span[@class='tab-group']/div[@class='module']/div[@class='infinite-tabs']/ul")
            for bill_tab in bill_tabs:
                for description in bill_tab.xpath("li[@class='module-item']"):
                    title = description.xpath("a")[0].text_content()
                    href = description.xpath("a/@href")[0]
                    match = bill_title_pattern.match(title)
                    if match:
                        self.scrape_current_bill(chamber, session, match.group(1).lower(), match.group(2), domain + href)

