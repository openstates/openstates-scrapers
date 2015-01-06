from billy.scrape.bills import BillScraper, Bill
from datetime import datetime
import lxml.html
import urllib

class NEBillScraper(BillScraper):
    jurisdiction = 'ne'

    def scrape(self, session, chambers):
        start_year = self.metadata['session_details'][session]['start_date'].year
        end_year = self.metadata['session_details'][session]['end_date'].year
        self.scrape_year(session, start_year)
        if start_year != end_year:
            self.scrape_year(session, end_year)

    def scrape_year(self, session, year):
        main_url = 'http://nebraskalegislature.gov/bills/search_by_date.php?SessionDay=%s' % year
        page = self.urlopen(main_url)
        page = lxml.html.fromstring(page)

        for docs in page.xpath('//div[@class="cal_content_full"]/table[@id="bill_results"]/tr/td[1]/a'):
            bill_abbr = docs.text

            #POST request for search form
            post_dict = {'DocumentNumber': bill_abbr, 'Legislature': session}
            #headers = urllib.urlencode(post_dict)
            bill_page = self.urlopen( 'http://nebraskalegislature.gov/bills/search_by_number.php',
                                     method="POST", body=post_dict)
            bill_link = bill_page.response.url

            #scrapes info from bill page
            self.bill_info(bill_link, session, main_url, bill_page)

    #Scrapes info from the bill page
    def bill_info(self, bill_link, session, main_url, bill_page):

        bill_page = lxml.html.fromstring(bill_page)

        #basic info
        try:
            long_title = bill_page.xpath('//div[@id="content_text"]/h2')[0].text.split()
        except IndexError:
            return None
        bill_id = long_title[0]
        title = ''
        for x in range(2, len(long_title)):
            title += long_title[x] + ' '
        title = title[0:-1]

        if not title:
            self.error('no title, skipping %s', bill_id)
            return

        #bill_type
        bill_type = 'resolution' if 'LR' in bill_id else 'bill'

        bill = Bill(session, 'upper', bill_id, title, type = bill_type)

        #sources
        bill.add_source(main_url)
        bill.add_source(bill_link)

        #Sponsor
        introduced_by = bill_page.xpath('//div[@id="content_text"]/div[2]/table/tr[2]/td[1]/a[1]')[0].text
        bill.add_sponsor('primary', introduced_by)

        #actions
        for actions in bill_page.xpath('//div[@id="content_text"]/div[3]/table/tr[1]/td[1]/table/tr'):
            date = actions[0].text
            if 'Date' not in date:
                date = datetime.strptime(date, '%b %d, %Y')
                action = actions[1].text_content()

                if 'Governor' in action:
                    actor = 'Governor'
                elif 'Speaker' in action:
                    actor = 'Speaker'
                else:
                    actor = 'upper'

                action_type = self.action_types(action)
                bill.add_action(actor, action, date, action_type)

        # were in reverse chronological order
        bill['actions'].reverse()

        #versions
        for versions in bill_page.xpath('//div[@id="content_text"]/div[2]/table/tr[2]/td[2]/a'):
            version_url = versions.attrib['href']
            version_url = 'http://nebraskalegislature.gov/' + version_url[3:len(version_url)]
            version_name = versions.text
            # replace Current w/ session number
            version_url = version_url.replace('Current', session)
            bill.add_version(version_name, version_url,
                             mimetype='application/pdf')


        #documents
        # this appear to be same as versions, dropped for now
        #for additional_info in bill_page.xpath('//div[@id="content_text"]/div[2]/table/tr[2]/td/a'):
        #    document_name = additional_info.text
        #    document_url = additional_info.attrib['href']
        #    document_url = 'http://nebraskalegislature.gov/' + document_url[3:len(document_url)]
        #    if '.pdf' in document_url:
        #        bill.add_document(document_name, document_url)

        #amendments
        for admendments in bill_page.xpath('//div[@id="content_text"]/div[3]/table/tr[1]/td[2]/table/tr/td/a'):
            admendment_name = admendments.text
            admendment_url = admendments.attrib['href']
            admendment_url = 'http://nebraskalegislature.gov/' + admendment_url[3:len(admendment_url)]
            bill.add_document(admendment_name, admendment_url)

        #related transcripts
        for transcripts in bill_page.xpath('//div[@id="content_text"]/div[3]/table/tr[2]/td[2]/a'):
            transcript_name = transcripts.text
            transcript_url = transcripts.attrib['href']
            bill.add_document(transcript_name, transcript_url)

        self.save_bill(bill)


    #Setting action types
    def action_types(self, action):

        if 'Date of introduction' in action:
            action_type = 'bill:introduced'
        elif 'Referred to' in action:
            action_type = 'committee:referred'
        elif 'Indefinitely postponed' in action:
            action_type = 'committee:failed'
        elif ('File' in action) or ('filed' in action):
            action_type = 'bill:filed'
        elif 'Placed on Final Reading' in action:
            action_type = 'bill:reading:3'
        elif 'Passed' in action or 'President/Speaker signed' in action:
            action_type = 'bill:passed'
        elif 'Presented to Governor' in action:
            action_type = 'governor:received'
        elif 'Approved by Governor' in action:
            action_type = 'governor:signed'
        elif 'Failed to pass notwithstanding the objections of the Governor' in action:
            action_type = 'governor:vetoed'
        elif 'Failed' in action:
            action_type = 'bill:failed'
        elif 'Bill withdrawn' in action:
            action_type = 'bill:withdrawn'
        else:
            action_type = ''
        return action_type
