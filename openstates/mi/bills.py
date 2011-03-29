import datetime
import re

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

BASE_URL = 'http://www.legislature.mi.gov'

class MIBillScraper(BillScraper):
    state = 'mi'

    def scrape_bill(self, chamber, session, bill_id):
        # try and get bill for current year
        html = self.urlopen('http://legislature.mi.gov/doc.aspx?%s-%s'
                            % (session[:4], bill_id.replace(' ', '-')))
        # if first page isn't found, try second year
        if 'Page Not Found' in html:
            html = self.urlopen('http://legislature.mi.gov/doc.aspx?%s-%s'
                                % (session[-4:], bill_id.replace(' ','-')))
            if 'Page Not Found' in html:
                return None

        doc = lxml.html.fromstring(html)

        title = doc.xpath('//span[@id="frg_billstatus_ObjectSubject"]')[0].text_content()

        bill = Bill(session=session, chamber=chamber, bill_id=bill_id,
                    title=title)

        # sponsors
        sp_type = 'primary'
        for sponsor in doc.xpath('//span[@id="frg_billstatus_SponsorList"]/a/text()'):
            bill.add_sponsor(sp_type, sponsor)
            sp_type = 'cosponsor'

        # actions (skip header)
        for row in doc.xpath('//table[@id="frg_billstatus_HistoriesGridView"]/tr')[1:]:
            tds = row.xpath('td')  # date, journal link, action
            date = tds[0].text_content()
            journal = tds[1].text_content()
            action = tds[2].text_content()
            date = datetime.datetime.strptime(date, "%m/%d/%Y")
            # instead of trusting upper/lower case, use journal for actor
            actor = 'upper' if journal[0] == 'S' else 'lower'
            bill.add_action(actor, action, date)

        # versions
        for row in doc.xpath('//table[@id="frg_billstatus_DocumentGridTable"]/tr'):
            version = self.parse_doc_row(row)
            if version:
                bill.add_version(*version)

        # documents
        for row in doc.xpath('//table[@id="frg_billstatus_HlaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                bill.add_document(*document)
        for row in doc.xpath('//table[@id="frg_billstatus_SfaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                bill.add_document(*document)

        self.save_bill(bill)
        return True

    def scrape(self, chamber, session):
        if chamber == 'upper':
            bill_no = 1
            abbr = 'SB'
        else:
            bill_no = 4001
            abbr = 'HB'

        # keep trying bills until scrape_bill returns None
        while True:
            if not self.scrape_bill(chamber, session,
                                    '%s %04d' % (abbr, bill_no)):
                break
            bill_no += 1

    def parse_doc_row(self, row):
        # first anchor in the row is HTML if present, otherwise PDF
        a = row.xpath('.//a')
        if a:
            name = row.xpath('.//b/text()')[0]
            url = BASE_URL + a[0].get('href').replace('../', '')
            return name, url

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
