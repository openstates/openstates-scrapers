from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from datetime import datetime
import lxml.html

class NEBillScraper(BillScraper):
    state = 'ne'

    def scrape(self, chamber, term):        
        years = {'102' : 2011}
        main_url = 'http://nebraskalegislature.gov/bills/search_by_date.php?SessionDay=%s' % (years[term])

        with self.urlopen(main_url) as page:
            page = lxml.html.fromstring(page)

            for docs in page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="cal_content_full"]/table[@id="bill_results"]/tr/td[1]/a'):
                bill_link = docs.attrib['href']
                bill_link = 'http://nebraskalegislature.gov/' + bill_link
                with self.urlopen(bill_link) as bill_page:
                    bill_page = lxml.html.fromstring(bill_page)

                    #basic info
                    long_title = bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/h2')[0].text.split()
                    bill_id = long_title[0]
                    title = ''
                    for x in range(2, len(long_title)):
                        title += long_title[x] + ' '
                    title = title[0:-1]
                    bill = Bill(term, chamber, bill_id, title)
                    
                    #sources
                    bill.add_source(main_url)
                    bill.add_source(bill_link)
                    
                    #Sponsor
                    introduced_by = bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[2]/table/tr[2]/td[1]/a[1]')[0].text
                    bill.add_sponsor('primary', introduced_by)

                    #actions
                    for actions in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[3]/table/tr[1]/td[1]/table/tr'):
                        date = actions[0].text
                        if 'Date' not in date:
                            date = datetime.strptime(date, '%b %d, %Y')
                            action = actions[1].text
                            if 'Governor' in action:
                                actor = 'Governor'
                            elif 'Speaker' in action:
                                actor = 'Speaker'
                            else:
                                actor = chamber
                            bill.add_action(actor, action, date, None)
                    self.save_bill(bill)
