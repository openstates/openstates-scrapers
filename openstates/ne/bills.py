from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
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

                    long_title = bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/h2')[0].text.split()
                    bill_id = long_title[0]
                    title = ''
                    for x in range(2, len(long_title)):
                        title += long_title[x] + ' '
                    title = title[0:-1]
                    bill = Bill(term, chamber, bill_id, title)
                    
                    bill.add_source(main_url)
                    bill.add_source(bill_link)
                    
                    introduced_by = bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[2]/table/tr[2]/td[1]/a[1]')[0].text
                    bill.add_sponsor('primary', introduced_by)

                    date_introduced = bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[2]/table/tr[2]/td[1]/a[2]')[0].text
                    #print date_introduce
                    print bill_id
                    for actions in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[3]/table/tbody/tr[1]/td[1]/table/tr'):
                        date = actions.xpath('/td[1]')[0].text
                        print date
                    #self.save_bill(bill)
