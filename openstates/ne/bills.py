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
                    #bill = Bill(term, chamber, bill_id, title)

                    #bill_type
                    if 'LR' in bill_id:
                        bill_type = 'resolution'
                    else:
                        bill_type = 'bill'

                    bill = Bill(term, chamber, bill_id, title, type = bill_type)
                    
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

                            if '-' in action:
                                vote_info = action.split()[-1].split('-')
                                yes_count = int(vote_info[0])
                                no_count = int(vote_info[1])
                                abstention_count = int(vote_info[2])
                                if yes_count > no_count:
                                    passed = True
                                else:
                                    passed = False
                                vote = Vote(chamber, date, action, passed, yes_count, no_count, abstention_count)
                                vote.add_source(bill_link)
                                bill.add_vote(vote)

                            if 'Governor' in action:
                                actor = 'Governor'
                            elif 'Speaker' in action:
                                actor = 'Speaker'
                            else:
                                actor = chamber

                            action_type = self.action_types(action)
                            bill.add_action(actor, action, date, action_type)
                    
                    #versions
                    for versions in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[2]/table/tr[2]/td[2]/a'):
                        version_url = versions.attrib['href']
                        version_url = 'http://nebraskalegislature.gov/' + version_url[3:len(version_url)]
                        version_name = versions.text
                        bill.add_version(version_name, version_url)

                        
                    #documents
                    #additional_info
                    for additional_info in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[2]/table/tr[2]/td/a'):
                        document_name = additional_info.text
                        document_url = additional_info.attrib['href']
                        document_url = 'http://nebraskalegislature.gov/' + document_url[3:len(document_url)]
                        if '.pdf' in document_url:
                            bill.add_document(document_name, document_url)

                    #amendments
                    for admendments in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[3]/table/tr[1]/td[2]/table/tr/td/a'):
                        admendment_name = admendments.text
                        admendment_url = admendments.attrib['href']
                        admendment_url = 'http://nebraskalegislature.gov/' + admendment_url[3:len(admendment_url)]
                        bill.add_document(admendment_name, admendment_url)

                    #related transcripts
                    for transcripts in bill_page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[3]/table/tr[2]/td[2]/a'):
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
        elif 'Passed' in action:
            action_type = 'bill:passed'
        elif 'Presented to Governor' in action:
            action_type = 'governor:received'
        elif 'Approved by Governor' in action:
            action_type = 'governor:signed'
        elif 'Failed to pass notwithstanding the objections of the Governor' in action:
            action_type = 'governor:vetoed'
        elif 'Failed' in action:
            action_type = 'bill:failed'
        else:
            action_type = ''
        return action_type
