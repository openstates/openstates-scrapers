from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html
import re, contextlib, itertools, urllib
import datetime as dt

class ORBillScraper(BillScraper):
    state = 'or'
       
    @contextlib.contextmanager
    def lxml_context(self, url, sep=None, sep_after=True):
        try:
            body = self.urlopen(url)
        except:
            body = self.urlopen("http://www.google.com")
        
        if sep != None: 
            if sep_after == True:
                before, itself, body = body.rpartition(sep)
            else:
                body, itself, after = body.rpartition(sep)    
        
        elem = lxml.html.fromstring(body)
        
        try:
            yield elem
        except:
            raise
        
    def clean_space(self, str):
        new_str = ' '.join(str.split())
        return new_str
                    
    def scrape(self, chamber, year):    
        bills_link = 'http://www.leg.state.or.us/bills_laws/billsinfo.htm'
        bills_sessions_pages = []
        
        with self.lxml_context(bills_link) as bills_page:
            for element, attribute, link, pos in bills_page.iterlinks():
                match = re.search("..(/measures[0-9]{2}s?.html)", link)
                if match != None:
                    bills_sessions_pages.append("http://www.leg.state.or.us" + match.group(1))
        
        shortened_year = int(year) % 100
        
        if shortened_year == 00:
            return
        
        pages_for_year = []
        
        for bsp in bills_sessions_pages:
            if str(shortened_year) in bsp:
                pages_for_year.append(bsp)
     
        measure_pages = []
        bill_pages_directory = []
     
        for pfy in pages_for_year:
            with self.lxml_context(pfy) as year_bills_page:
                for element, attribute, link, pos in year_bills_page.iterlinks():
                    if chamber == 'upper':
                        link_part = 'senmh'
                    else:
                        link_part = 'hsemh'
                    
                    regex = "([0-9]{2}(reg|ss[0-9]))/pubs/" + link_part + ".(html|txt)"
                    match = re.search(regex, link)

                    if match != None:
                        measure_pages.append("http://www.leg.state.or.us/" + match.group(0))
                        bill_pages_directory.append("http://www.leg.state.or.us/" + match.group(1) + "/measures/main.html")
                        
        bill_pages = [] 
        
                 
             
        for bp in bill_pages_directory:
            with self.lxml_context(bp) as bills_page:
                for element, attribute, link, pos in bills_page.iterlinks():
                    if re.search(' +.html +', link)!= None:
                        continue
                    
                    base_link = bp.rstrip('main.html')

                    if chamber == 'upper':
                        if link[0] == 's':
                            bill_pages.append(base_link + link.translate(None, '\n'))                      
                    else:
                        if link[0] == 'h':
                            bill_pages.append(base_link + link.translate(None, '\n')) 
                            
        # Remove unnecesary link 
        bill_pages.pop(0)
        
        bills_dict = {}

        for bp in bill_pages:
            with self.lxml_context(bp) as bills_page:
                bills = bills_page.cssselect('a')
                for b in bills:
                    bill_description = b.text_content()
                    title, sep, version = bill_description.partition('-')
                    splitted_title = title.split()
                    bill_number = splitted_title[-1]
                    splitted_title.pop(-1)
                    initials = ''
                    for t in splitted_title:
                        initials += t[0]
                    
                    key = initials + ' ' + bill_number.lstrip('0')
                    link = b.iterlinks().next()[2]
                   
                    try: 
                        bills_dict[key]
                    except KeyError:
                        bills_dict[key] = []
                    
                    bills_dict[key].append((version, base_link + link))
        
        if chamber == 'upper':
            markers = ('SB', 'SR', 'SJR', 'SJM', 'SCR', 'SM')
        else:
            markers = ('HB', 'HR', 'HJR', 'HJM', 'HCR', 'JM')
            
        bill_info = {}
        
        for mp in measure_pages:  
            with self.lxml_context(mp) as measure_page:
                measures = measure_page.text_content()
                lines = measures.split('\n')
                
                raw_date = ''
                action_party = ''
                key = ''
                text = ''
                actions = []
                first_bill = True
                
                for line in lines:
                    date_match = re.search('([0-9]{1,2}-[0-9]{1,2})(\((S|H)\))? ', line)
                    
                    marker_in_line = False
                    for marker in markers:
                        if marker in line[0:2]:
                            marker_in_line = True
                            break
                         
                    if marker_in_line:                    
                        if not first_bill:
                            value = bill_info[key]
                            date = dt.datetime.strptime(raw_date + '-' + year, '%m-%d-%Y')
                            actions.append((date, action_party, self.clean_space(text)))
                            value.append(actions)
                            actions = []
                            
                        else:
                            first_bill = False
                            
                        new_bill = True  
                        regex = marker + ' +[0-9]{1,4}'       
                        key_match = re.search(regex, line)
                        if key_match == None:
                            print line
                            print regex
                        key  = self.clean_space(key_match.group(0))
                        text = line.split(key)[1]                 
                    
                    elif date_match != None:
                        if new_bill:
                            bill_info[key] = [self.clean_space(text)]
                            print self.clean_space(text)
                            print 
                            new_bill = False
                        
                        else:
                            date = dt.datetime.strptime(raw_date + '-' + year, '%m-%d-%Y')
                            actions.append((date, action_party, self.clean_space(text)))
                            
                        raw_date = date_match.group(1)
                        action_party = date_match.group(2)                
                        text = line.split(date_match.group(0))[1]
                            
                    elif line.isspace():
                        continue
                    
                    elif '---' in line:
                        continue
                         
                    else:
                        text = text + ' ' + line
                        
#            for key, value in bill_info.iteritems():
#                print key
#                text = value[0]
#                print text
#                actions = value[1]
#                for a in actions:
#                    print a[0]
#                    print a[1]
#                    print a[2]

                
                    
                
                

                        
                           
                        
                    
                