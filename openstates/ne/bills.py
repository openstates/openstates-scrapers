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

            for docs in page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="cal_content_full"]/table[@id="bill_results"]/tr[@class="row1"]'):
                bill_id = docs.xpath('td[1]/a')[0].text
                prime_leg = docs.xpath('td[2]/a')[0].text
                status = docs.xpath('td[3]')[0].text.strip()
                title = docs.xpath('td[4]')[0].text.strip()
                bill = Bill(term, chamber, bill_id, title)
                bill.add_source(main_url)
                
                link = docs.attrib['href']
                print link

            #for docs in page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="cal_content_full"]/table[@id="bill_results"]/tr[@class="row2"]'):
            #    name = docs.xpath('td[1]/a')[0].text
            #    print bill
