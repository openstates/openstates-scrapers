import datetime as dt
import re

from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape import NoDataForPeriod

from BeautifulSoup import BeautifulSoup

BASE_URL = 'http://www.legislature.mi.gov'

class MIBillScraper(BillScraper):
    state = 'mi'

    def scrape(self, chamber, session):
        self.validate_session(session)

        if chamber == 'upper':
            bill_no = 1
            abbr = 'SB'
        else:
            bill_no = 4001
            abbr = 'HB'
        while True:
            bill_page = self.scrape_bill(session, abbr, bill_no)
            bill_page = BeautifulSoup(bill_page)
            # if we can't find a page, we must be done. This is a healthy thing.
            if bill_page == None: return
            title = ''.join(self.flatten(bill_page.findAll(id='frg_billstatus_ObjectSubject')[0]))
            title = title.replace('\n','').replace('\r','')
            bill_id = "%s %d" % (abbr, bill_no)

            the_bill = Bill(session, chamber, bill_id, title)

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

            self.parse_actions(the_bill, bill_page.findAll(id='frg_billstatus_HistoriesGridView')[0])
            self.save_bill(the_bill)
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
        with self.urlopen(url) as journal:
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
                vote = self.parse_vote(the_bill, journal_meta, action, really_last_action, dt.datetime.strptime(last_date.string, '%m/%d/%Y'))
                continue
            elif re.match("\s+$", date.string) and 'time:' in action.lower():
                continue
            
            # pull out the link to the journal for roll calls
            if journal.a:
                journal_meta = re.findall(r'objectname\=(\d{4}\-\w\w\-\d+-\d+\-\d+)', journal.a['href'])[0]
            

            if re.match('.*?Roll Call\s(?:#|(?:No\.))\s(\d+)', action, re.I):
                vote = self.parse_vote(the_bill, journal_meta, action, really_last_action, dt.datetime.strptime(date.string, '%m/%d/%Y'))

            # Instead of just *saying* what chamber performed an action
            # They use uppercase or lowercase to denote it. Unless the first
            # word in a lowercase sentance is a proper noun, then that's uppercase too.
            chamber = 'lower' if action[1].islower() else 'upper'
            the_bill.add_action(chamber, action, dt.datetime.strptime(date.string, '%m/%d/%Y'))

    def scrape_bill(self, session, chamber, number):
        number = "%04d" % number
        with self.urlopen('http://legislature.mi.gov/doc.aspx?%s-%s-%s' % (session[:4], chamber, number)) as html:
            if 'Page Not Found' not in html:
                return html

        # they change years when a new year starts. HOW ODD
        with self.urlopen('http://legislature.mi.gov/doc.aspx?%s-%s-%s' % (session[-4:], chamber, number)) as bill:
            if 'Page Not Found' not in html:
                return html


    def flatten(self, tree):
        if tree.string:
            s = tree.string
        else:
            s = map(lambda x: self.flatten(x), tree.contents)
        if len(s) == 1:
            s = s[0]
        return s
