from datetime import datetime
import lxml.html
from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote

class NDBillScraper(BillScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the openstates  backend.
    """
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        
        #determining the start year of the term
        start_year = ((int(term) - 62)*2) + 2011

        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            norm_chamber_name = 'Senate'
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'

        assembly_url = '/assembly/%s-%s' % (term, start_year)

        chamber_url = '/bill-text/%s-bill.html' % (url_chamber_name)

        bill_list_url = self.site_root + assembly_url + chamber_url

        with self.urlopen(bill_list_url) as html:
            list_page = lxml.html.fromstring(html)
            # connects bill_id with bill details page
            bills_url_dict = {}
            #connects bill id with bills to be accessed later.
            bills_id_dict = {}
            title = ''
            for bills in list_page.xpath('/html/body/table[3]/tr/th/a'):
                bill_id = bills.text
                bill_url = bill_list_url[0: -26] + '/' + bills.attrib['href'][2:len(bills.attrib['href'])]
                bill_type = self.bill_type_info(bill_id)
                bill = Bill(term, chamber, bill_id, title, bill_type=bill_type)
                
                #sources
                bill.add_source(bill_url)
                bill.add_source(bill_list_url)
                
                #storing bills to be accessed
                bills_url_dict[bill_id] = bill_url
                bills_id_dict[bill_id] = bill

            #bill details page
            for bill_keys in bills_url_dict.keys():
                url = bills_url_dict[bill_keys]
                curr_bill = bills_id_dict[bill_keys]
                with self.urlopen(url) as bill_html:
                    bill_page = lxml.html.fromstring(bill_html)
                    for bill_info in bill_page.xpath('/html/body/table[4]/tr/td'):
                        info = bill_info.text

                        #Sponsors
                        if "Introduced" in info:
                            if ('Rep' in info) or ('Sen' in info):
                                rep = info[14: 17]
                                info = info[18: len(info)]
                                sponsors = info.split(',')
                            else:
                                sponsors = info[13: len(info)]
                                rep = ''
                            for sponsor in sponsors:
                                if sponsor == sponsors[0]:
                                    sponsor_type = 'primary'
                                else:
                                    sponsor_type = 'cosponsor'
                                curr_bill.add_sponsor(sponsor_type, rep + sponsor)
                        else:
                            #title
                            title = info.strip()
                            curr_bill["title"] = title


                    #actions
                    last_date = datetime
                    last_actor = ''
                    action_num = len(bill_page.xpath('/html/body/table[5]//tr'))
                    for actions in range(2, action_num, 2):
                        path = '//table[5]/tr[%s]/' % (actions)
                        action_date = bill_page.xpath(path + 'th')[0].text.strip() + '/' + str(start_year)
                        action_actor = bill_page.xpath(path + 'td[2]')[0].text
                        action =  bill_page.xpath(path + 'td[4]')[0].text
                        
                        if action_actor == "":
                            action_actor = last_actor
                        last_actor = action_actor
                        action_actor = 'upper' if action_actor == 'senate' else 'lower' 

                        if action_date == ('/' + str(start_year)):
                            action_date = last_date
                        else:
                            action_date = datetime.strptime(action_date, '%m/%d/%Y')
                        last_date = action_date
                        curr_bill.add_action(action_actor, action, action_date, '')


                        #votes
                        if "yeas" in action:
                            yes_count = int(action.split()[action.split().index('yeas')+1])
                            no_count = action.split()[action.split().index('nays')+1]
                            no_count = int(no_count[0:-1]) if ',' in no_count else int(no_count)
                            passed = True if yes_count > no_count else False
                            vote_type = self.vote_type_info(action)

                            vote = Vote(action_actor, action_date, action, passed, yes_count, no_count, 0, vote_type)
                            curr_bill.add_vote(vote)

                        #document within actions
                        doc_num_pos = len(bill_page.xpath(path + 'td'))
                        if doc_num_pos >5:
                            doc_name = bill_page.xpath(path + 'td[6]/a')[0].attrib['href']
                            doc_url = url[0: url.find('bill')].replace('///', '/') + doc_name[3:len(doc_name)]
                self.save_bill(curr_bill)

    #Returns action type
    def vote_type_info(self, action):
        if "Second reading" in action:
            vote_type = 'reading:2'
        elif "reading" in action:
            vote_type = 'reading:1'
        elif "Override" in action:
            vote_type = 'veto_override'
        elif "Amendment" in action:
            vote_type = 'amendment'
        else:
            vote_type = 'other'
        return vote_type

    #Returns bill type
    def bill_type_info(self, bill_id):
        if (int(bill_id) > 1000) and (int(bill_id) < 3000):
            bill_type = 'bill'
        elif (int(bill_id) > 3000) and (int(bill_id) < 5000):
            bill_type = 'concurrent resolution'
        elif(int(bill_id) > 5000) and (int(bill_id) < 7000):
            bill_type = 'resolution'
        elif (int(bill_id) > 7000) and (int(bill_id) < 9000):
            bill_type = 'memorial'
        return bill_type
