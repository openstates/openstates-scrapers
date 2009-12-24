#!/usr/bin/env python
import sys
sys.path.append('./scripts')
import datetime as dt, time
import re

from pyutils.legislation import LegislationScraper, NoDataForYear, ScrapeError, Legislator, Bill, Vote

from BeautifulSoup import BeautifulSoup
from pyPdf import PdfFileReader
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, process_pdf
from pdfminer.pdfdevice import PDFDevice
from pdfminer.converter import TextConverter
from pdfminer.cmap import CMapDB, find_cmap_path
from pdfminer.layout import LAParams
from StringIO import StringIO
import urllib2
import warnings
warnings.simplefilter ( "ignore", DeprecationWarning)

BASE_URL = 'http://www.legislature.mi.gov'
class MichiganScraper(LegislationScraper):
    #must set state attribute as the state's abbreviated name
    state = 'mi'
    earliest_year = 1999

    def scrape_legislators(self,chamber,year):
        if int(year) %2 == 0:  
            raise NoDataForYear(year)

        if int(year) < time.localtime()[0]:
            self.scrape_past_legislators(chamber, year)
        else:
            self.scrape_current_legislators(chamber, year)

    def scrape_current_legislators(self, chamber, year):
        abbr = {'D': 'Democrat', 'R': 'Republican'}
        if chamber=='lower': 
            with self.soup_context('http://house.michigan.gov/replist.asp') as legs:
                for leg in legs.findAll('table', text='First Name'):
                    for tr in leg.parent.parent.parent.parent.parent.findAll('tr'):  #a - font - th - tr - table
                        if tr.findAll('th') != []: continue
                        (district, last_name, first_name, party) = tr.findAll('td', limit=4)
                        if last_name.div.a.font.string is None: continue
                        last_name = last_name.div.a.font.string.strip()
                        first_name = first_name.div.a.font.string.strip()
                        district = district.div.font.string.strip()
                        party = abbr[party.div.font.string.strip()]
                        leg = Legislator(year, chamber, district, first_name + " " + last_name, first_name, last_name, '', party)
                        self.add_legislator(leg)
        else: 
            with self.soup_context('http://www.senate.michigan.gov/SenatorInfo/alphabetical_list_of_senators.htm') as legs:
                for tr in legs.findAll('tr'):
                    tds = tr.findAll('td', limit=4)
                    if len(tds) != 4: continue
                    (name, hometown , district, party) = tds
                    if name.font is None or name.font.a is None: continue
                    #if district.string is None: continue
                    name = name.font.a.string.strip().replace('\n','')
                    whitespace = re.compile('\s+')
                    name = whitespace.sub(' ', name)
                    name = name.split(', ')
                    name = "%s %s" % (name[1], name[0]) #.reverse() didn't work and I didn't care
                    (first, middle, last, suffix) = self.parse_name(name)
                    if district.p: district = district.p.a.font.string.strip()
                    elif district.a: district = district.a.font.string.strip()
                    else: continue 

                    party = party.font.string.strip()
                    leg = Legislator(year, chamber, district, name, first.strip(), last.strip(), middle.strip(), party, suffix=suffix)
                    self.add_legislator(leg)

    def scrape_past_legislators(self, chamber, year):
        year = int(year)
        # Michiganders!

        # we're looking at one of two tables, and the most reliable way to tell them
        # apart is by the number of links in them. Thankfully, it seems to work.
        with self.soup_context("http://www.legislature.mi.gov/mileg.aspx?page=MM%d-%d&chapter=3" % (year, year+1)) as tables:
           for table in tables.findAll('table'):
               links = table.findAll('a')
               if len(links) == 38 and chamber == 'upper':
                   for a in links: self.fetch_past_legislator(str(year), chamber, a['href'], a.string)
               elif len(links) == 110 and chamber == 'lower':
                   for a in links: self.fetch_past_legislator(str(year), chamber, a['href'], a.string)    
       

    # literally the most fragile code I've ever written
    def fetch_past_legislator(self, year, chamber, url, name):
        name = name.replace('\n','')
        spaces = re.compile("\s+")
        name = spaces.sub(' ', name)

        url = "http://www.legislature.mi.gov/%s" % url.replace('../', '')
        with self.urlopen_context(url) as the_pdf:
    
            # UGH! What a useful yet convoluted library.
            outtext = StringIO()
            rsrc = PDFResourceManager(CMapDB(find_cmap_path()))
            device = TextConverter(rsrc, outtext, codec='ascii', laparams=LAParams())
            process_pdf(rsrc, device, StringIO(the_pdf), set())
            outtext.seek(0)
            text = outtext.read()
            # I should just add a pdf_context that wraps this :-\
            
            res = re.findall(r'State\s+(?:Senator|Representative)\n(.*?)\n([R|D]).*?[\n]*(\d+)(?:st|nd|rd|th)', text)
            if res == []: 
                print text
                raise Exception("Some fragile code broke.") 
            name = res[0][0]
            (first, middle, last, suffix) = self.parse_name(name)
            leg = Legislator(year, chamber, res[0][2], name, first , last, middle, res[0][1], suffix=suffix)
            self.add_legislator(leg)

    def scrape_bills(self,chamber,year):
        if int(year) %2 == 0:  
            raise NoDataForYear(year)
        # 
        year = int(year)
        oyear = year #save off the original of the session
        if chamber == 'upper':
            bill_no = 1
            abbr = 'SB'
        else:
            bill_no = 4001
            abbr = 'HB'
        while True:
            (bill_page,year) = self.scrape_bill(year, abbr, bill_no)
            # if we can't find a page, we must be done. This is a healthy thing.
            if bill_page == None: return
            title = ''.join(self.flatten(bill_page.findAll(id='frg_billstatus_ObjectSubject')[0]))
            title = title.replace('\n','').replace('\r','')
            bill_id = "%s %d" % (abbr, bill_no)

            the_bill = Bill("Regular Session %d" % oyear, chamber, bill_id, title)

            #sponsors
            first = 0
            for name in bill_page.findAll(id='frg_billstatus_SponsorList')[0].findAll('a'):
                the_bill.add_sponsor(['primary', 'cosponsor'][first], name.string)
                first = 1

            #versions
            for doc in bill_page.findAll(id='frg_billstatus_DocumentGridTable')[0].findAll('tr'):
                r = self.parse_doc(the_bill, doc)
                if r: the_bill.add_version(*r)

            #documents
            if 'frg_billstatus_HlaTable' in str(bill_page):
                for doc in bill_page.findAll(id='frg_billstatus_HlaTable')[0].findAll('tr'):
                    r = self.parse_doc(the_bill, doc)
                    if r: the_bill.add_document(*r)
            if 'frg_billstatus_SfaSection' in str(bill_page):
                for doc in bill_page.findAll(id='frg_billstatus_SfaSection')[0].findAll('tr'):
                    r = self.parse_doc(the_bill, doc)
                    if r: the_bill.add_document(*r)

            the_bill.add_source('http://legislature.mi.gov/doc.aspx?%d-%s-%04d' % (year, abbr, bill_no))
            self.parse_actions(the_bill, bill_page.findAll(id='frg_billstatus_HistoriesGridView')[0])
            self.add_bill(the_bill)
            bill_no = bill_no + 1
        pass

    def parse_doc(self, the_bill, row):
        (docs, words) = row.findAll('td')
        url = None
        if '.htm' in str(docs): url = docs.findAll('a', href=re.compile('.htm'))
        elif '.pdf' in str(docs): url = docs.findAll('a', href=re.compile('.pdf'))
 
        if url: return (words.b.string, "%s/%s" % (BASE_URL, url[0]['href'].replace('../','')))
        else: return None

    def parse_vote_table(self, table):
        members = []
        for cell in table.findAll('td'):
            if cell.font: members.append(cell.font.string)
            else: found = cell
     
        return members

    # votes aren't shown anywhere besides the journals, but the journals are
    # relatively easy to parse. 
    def parse_vote(self, the_bill, journal_meta, action, motion, the_date):	
        abbr = {'HJ': 'House', 'SJ': 'Senate'}
        updown = {'HJ': 'lower', 'SJ': 'upper'}
        (year,house,rest) = journal_meta.split('-', 2)

        # try and get the vote counts from the action summary. if not, trigger an error later on
        # that we can use to find out which action on which bill is malformed.
        votes = re.findall('YEAS (\d+)\s*NAYS (\d+)(?:[\sA-Z]+)*\s*(\d*)(?:[\sA-Z]+)*\s*(\d*)', action, re.I)
        if votes != []:
            (yeas, nays, o1, o2) = map(lambda x: 0 if x=='' else int(x), votes[0])
        else:
            (yeas, nays, o1, o2) = [0,0,0,0]
            print action

        the_vote = Vote(updown[house], the_date, motion, (yeas > nays), yeas, nays, o1+o2)
        # get the right 1999-2000 type string built.
        if int(year) % 2 == 0: year = "%d-%s" % (int(year)-1, year)
        else: year = "%s-%d" % (year, int(year)+1)

        # find the roll call number from the action
        number = re.findall('Roll Call\s(?:#|(?:No\.))\s(\d+)', action, re.I)
        # if we can't, die.
        if not number: return 
        number = int(number[0])

        url = "http://www.legislature.mi.gov/documents/%s/Journal/%s/htm/%s.htm" % (year, abbr[house], journal_meta)
        with self.urlopen_context(url) as journal:
            # clean up a few things
            journal = str(journal).replace('&nbsp;', ' ').replace('&#009;', '\t')
            # substring searching: The Best Way To Do Things
            start = re.search('<B>Roll Call No.(?:\s*)%d' % number, journal, re.I)
            if not start: # This roll wasn't found -- sometimes they screw up the journal no.
                the_bill.add_vote(the_vote)
                self.log("Couldn't find roll #%d" % number)
                return the_vote
            else:
                start = start.start()
            
            end = journal.index('In The Chair:', start)


            byline = 'yea' #start with *something*
            vote_type = the_vote.yes
            votes,names = [],[]
            # the -24 is a super fragile way of getting to the <p> tag before the <b>
            for line in BeautifulSoup(journal[start-24:end]).contents:
                line = str(line)
                # check to see if we need to flip the vote type
                last_byline = byline
                last_vote_type = vote_type
                if 'Yeas' in line: vote_type, byline = the_vote.yes, 'yea'
                elif 'Nays' in line: vote_type, byline = the_vote.no, 'nay'
                elif 'Excused' in line: vote_type, byline = the_vote.other, 'excused'
                elif 'Not Voting' in line: vote_type, byline = the_vote.other, 'not voting'

                # remove empty names
                names = filter(lambda n: not re.match('^\s*$', n), names)
                # add names to the vote list for this type
                if last_byline != byline:
                    # save the votes
                    map(lambda x: votes.append(x), names)
                    map(lambda x: last_vote_type(x), votes)
                    #print "changing %s %s" % (last_byline, votes)
                   
                    votes = []
                    names = []
                    continue
                else:
                    map(lambda x: votes.append(x), names)

                names = []
                # votes are listed in a few different ways. it's a blast.
                soup = BeautifulSoup(line)
                if soup.table:
                    names = self.parse_vote_table(soup)
                elif soup.b: #bolds are headings, which we skip
                    continue
                elif soup.p and soup.p.font and soup.p.font.string is not None:
                    names = soup.p.font.string.split('\t')
                # sometimes we only have a <p>
                elif soup.p and soup.p.string is not None:
                    names = soup.p.string.split('\t')
                # and sometimes, we just get blank lines.
                elif '\t' in line:
                    names = line.split('\t')

        # out of the loop, add the last votes
        map(lambda x: last_vote_type(x), votes)

        # do some checking, but don't die if there's a problem. Usuaully it's just a bad heading.
        if the_vote['yes_count'] != len(the_vote['yes_votes']):
           self.log("Yea vote mismatch: %d expected, but saw %d" % (the_vote['yes_count'], len(the_vote['yes_votes'])))  
        elif the_vote['no_count'] != len(the_vote['no_votes']):
           self.log("Nay vote mismatch: %d expected, but saw %d" % (the_vote['no_count'], len(the_vote['no_votes'])))
        elif the_vote['other_count'] != len(the_vote['other_votes']):
           self.log("Other vote mismatch: %d expected, but saw %d" % (the_vote['other_count'], len(the_vote['other_votes'])))
        the_bill.add_vote(the_vote)
        
        return the_vote

    def parse_actions(self, the_bill, actions):
        date, last_action, action = None, None, None
        for action_line in actions.findAll('tr'):
            if action_line.findAll('th') != []: continue
            last_date = date
            really_last_action = last_action
            last_action = action
            (date, journal, action) = action_line.findAll('td')
            action = ''.join(self.flatten(action))
            # sometimes we get a blank line, and we need to go back a bit to see what 
            # we actually need to check.
            if re.match("\s+$", date.string) and 'time:' not in action.lower():
                try:
                    vote = self.parse_vote(the_bill, journal_meta, action, really_last_action, dt.datetime.strptime(last_date.string, '%m/%d/%Y'))
                except urllib2.HTTPError:
                    self.log("Error fetching rolls for \"%s\"" % action)
                continue
            elif re.match("\s+$", date.string) and 'time:' in action.lower():
                continue
            
            # pull out the link to the journal for roll calls
            if journal.a:
                journal_meta = re.findall(r'objectname\=(\d{4}\-\w\w\-\d+-\d+\-\d+)', journal.a['href'])[0]
            

            if re.match('.*?Roll Call\s(?:#|(?:No\.))\s(\d+)', action, re.I):
                try:
                    vote = self.parse_vote(the_bill, journal_meta, action, really_last_action, dt.datetime.strptime(date.string, '%m/%d/%Y'))
                except urllib2.HTTPError:
                    self.log("Error fetching rolls for \"%s\"" % action)

            # Instead of just *saying* what chamber performed an action
            # They use uppercase or lowercase to denote it. Unless the first
            # word in a lowercase sentance is a proper noun, then that's uppercase too.
            chamber = 'lower' if action[1].islower() else 'upper'
            the_bill.add_action(chamber, action, dt.datetime.strptime(date.string, '%m/%d/%Y'))

    def scrape_bill(self, year, chamber, number):
        number = "%04d" % number
        with self.soup_context('http://legislature.mi.gov/doc.aspx?%d-%s-%s' % (year, chamber, number)) as bill:
            if bill.findAll('span', text='Page Not Found') == []:
                return (bill, year)

        # they change years when a new year starts. HOW ODD
        with self.soup_context('http://legislature.mi.gov/doc.aspx?%d-%s-%s' % (year+1, chamber, number)) as bill:
            if bill.findAll('span', text='Page Not Found') == []:
               return (bill, year+1)
        return (None, year)

    def scrape_metadata(self): 
        return {
            'state_name': 'Michigan',
            'legislature_name': 'Michigan Legislature',
            'lower_chamber_name': 'House of Representatives',
            'upper_chamber_name': 'Senate',
            'lower_title': 'Representative',
            'upper_title': 'Senator',
            'lower_term': 2,
            'upper_term': 4,
            'sessions': ['1999', '2001', '2003', '2005', '2007', '2009'],
            'session_details': {
                '1999': {'years': [1999, 2000], 'sub_sessions': []},
                '2001': {'years': [2001, 2002], 'sub_sessions': []},
                '2003': {'years': [2003, 2004], 'sub_sessions': []},
                '2005': {'years': [2005, 2006], 'sub_sessions': []},
                '2007': {'years': [2007, 2008], 'sub_sessions': []},
                '2009': {'years': [2009, 2010], 'sub_sessions': []}
            }
        }

    def flatten(self, tree):
        if tree.string:
            s = tree.string
        else:
            s = map(lambda x: self.flatten(x), tree.contents)
        if len(s) == 1:
            s = s[0]
        return s
        
     #stealing from llimllib, since his works pretty well.
    def parse_name(self, name):
        nickname = re.findall('\".*?\"', name)
        nickname = nickname[0] if nickname else ''
        name = re.sub("\".*?\"", "", name).strip()
        names = name.split(" ")
        first_name = names[0]
        # The "Jody" Amedee case
        if len(names) == 1:
            first_name = nickname
            middle_name = ''
            last_name = names[0]
        elif len(names) > 2:
            middle_names = [names[1]]
            for i, n in enumerate(names[2:]):
                if re.search("\w\.$", n.strip()):
                    middle_names.append(n)
                else: break
            middle_name = " ".join(middle_names)
            last_name = " ".join(names[i+2:])
        else:
            middle_name = ""
            last_name = names[1]

        #steal jr.s or sr.s
        suffix = re.findall(", (\w*?)\.|(I+)$", last_name) or ""
        if suffix:
            suffix = suffix[0][0] or suffix[0][1]
            last_name = re.sub(", \w*?\.|(I+)$", "", last_name)

        return (first_name, middle_name, last_name, suffix)
if __name__ == '__main__':
    MichiganScraper().run()
