import re
import sys
sys.path.append('./scripts')
from pyutils.legislation import *
import datetime as dt, time
import random
from htmlentitydefs import name2codepoint

class ALLegislationScraper(LegislationScraper):
    state = 'al'
    internal_sessions = {}

    def scrape_legislators(self,chamber,year):
        if int(year) < time.localtime()[0] or int(year) not in self.internal_sessions:
            raise NoDataForYear(year)

        if chamber == 'upper':
            url = 'http://www.legislature.state.al.us/senate/senators/senateroster_alpha.html'
        else:
            url = 'http://www.legislature.state.al.us/house/representatives/houseroster_alpha.html'
        with self.soup_context(url) as names:
            for row in names.find('strong', text='District').parent.parent.parent.parent.parent.findAll('tr'):
                if "Office Phone" in str(row):
                    continue
                cells = row.findAll('td')
                name = cells[0].find('a')
                if name:
                    name = name.contents[0] if len(name.contents) > 1 else name
                    name = self.unescape(name.string)
                else:
                    continue
                #someone wanted to get in on the div/css bandwagon...
                if cells[1].find('div'):
                    party = cells[1].find('div').string
                elif cells[1].find('center'):
                    party = cells[1].find('center')
                else:
                    party = cells[1].string

                party = re.findall(r'\w', party.string)[0]

                if cells[2].find('div'):
                    district = cells[2].find('div')
                elif cells[2].find('center'):
                    district = cells[2].find('center')
                elif cells[2].find('p'):
                    district = cells[2].find('p')
                else:
                    district = cells[2]

                district = int(self.unescape(district.string).strip())
                (last_name,rest) = name.strip().split(', ',1)
                rest = rest.strip().split(' ')
                leg = Legislator(year, chamber, district, name, rest, last_name, '', party)
                self.add_legislator(leg)
        pass

    def scrape_bill(self, chamber, current_bill, session):
        other_chamber = 'upper' if chamber == 'lower' else 'lower'
        with self.soup_context("http://alisondb.legislature.state.al.us/acas/SESSBillsStatusResultsMac.asp?BillNumber=%s&GetStatus=Get+Status&session=%s" % (current_bill, session[0])) as bill:
             if "Your ACAS Session has expired." in str(bill):
                 raise Exception("Expired cookie - you'll have to run with -n to skip caching")
             try:
                 bill_id = int(re.findall(r'BTN([0-9]+)', str(bill))[0])
             except:
                 raise Exception("No bill found. Hopefully that means it's the end of the session") 
             title = bill.find("td", {'colspan': '7'}).string
             self.log("Starting parse of %s" % current_bill)
             #create our bill!
             bill = Bill(session[1], chamber, current_bill, title.strip())

             #add sponsors and co-sponsors
             with self.soup_context("http://alisondb.legislature.state.al.us/acas/ACTIONSponsorsResultsMac.asp?OID=%d" % bill_id) as sponsors:
                 # This pains me.
                 (primary,secondary) = sponsors.findAll("table", text="Co-Sponsors")[0].parent.parent.parent.findAll('table')
                 for p in primary.findAll('td'):
                     bill.add_sponsor('primary', p.string)
                 for s in secondary.findAll('td'):
                     bill.add_sponsor('cosponsor', s.string)
             with self.soup_context("http://alisondb.legislature.state.al.us/acas/ACTIONHistoryResultsMac.asp?OID=%d" % bill_id) as history:
                  actions = history.findAll('table', text="Committee")[0].parent.parent.parent.findAll('tr')
                  #Date Amend/Subst Matter Committee Nay Yea Abs Vote
                  for event in actions:
                       e = event.findAll('td')
                       if len(e) == 0:
                           continue
                       date = e[0].string
                       amend = e[1].find('input')
                       matter = e[2].string
                       y_votes = e[5].string
                       n_votes = e[4].string
                       a_votes = e[6].string
                       
                       
                       roll = e[7].find('input')
                       #(date, amend, matter, committee, nays, yeas, abs, vote_thing) = map(lambda x: x.string, e)
                       if date != None:
                           act_date = dt.datetime.strptime(date, '%m/%d/%Y')
                       if amend != None:
                           splitter = re.findall(r'documentSelected\(\'(\w*)\',\'([\w\d-]*)\',\'([\w\.\-]*)\',\'([\w\d/]*)\',\'([\w\d]*)\',\'([\w\s]*)\'', str(amend))[0]
                           amend = "http://alisondb.legislature.state.al.us/acas/%s/%s" % (splitter[3], splitter[2])
                           bill.add_document(matter, amend)

                       if roll != None: 
                          splitter = re.findall(r'voteSelected\(\'(\d*)\',\'(\d*)\',\'(\d*)\',\'(.*)\',\'(\d*)\'',str(roll))[0]
                          roll = "http://alisondb.legislature.state.al.us/acas/GetRollCallVoteResults.asp?MOID=%s&VOTE=%s&BODY=%s&SESS=%s" % (splitter[0], splitter[1], splitter[2], splitter[4])
                          with self.soup_context(roll) as votes:
                              vote_rows = votes.findAll('table', text='Member')[0].parent.parent.parent.findAll('tr')
                              
                              yea_votes = int(votes.findAll('tr', text='Total Yea:')[0].parent.parent.findAll('td')[2].string)
                              nay_votes = int(votes.findAll('tr', text='Total Nay:')[0].parent.parent.findAll('td')[2].string)
                              abs_votes = int(votes.findAll('tr', text='Total Abs:')[0].parent.parent.findAll('td')[2].string)
                              p_votes   = len(votes.findAll('tr', text='P'))
                              
                              #chamber, date, motion, passed, yes_count, no_count, other_count
                              vote = Vote(chamber, act_date, matter, (yea_votes > nay_votes), yea_votes, nay_votes, abs_votes + p_votes)
                              
                              vote.add_source(roll)
                              for row in vote_rows:
                                  skip = str(row)
                                  if "Total Yea" in skip or "Total Nay" in skip or "Total Abs" in skip:
                                      continue
                                  html_layouts_are_awesome = row.findAll('td')
                                  if len(html_layouts_are_awesome) == 0:
                                      continue
	
                                  (name, t) = html_layouts_are_awesome[0].string, html_layouts_are_awesome[2].string
                                  self.dumb_vote(vote, name, t)
                                  
                                  if len(html_layouts_are_awesome) > 3:
                                      (name, t) = html_layouts_are_awesome[4].string, html_layouts_are_awesome[6].string
                                      self.dumb_vote(vote, name, t)
                              bill.add_vote(vote)

                       if y_votes != None:
                           yea_votes = self.dumber_vote(y_votes)
                           nay_votes = self.dumber_vote(n_votes)
                           abs_votes = self.dumber_vote(a_votes)
                           vote = Vote(chamber, act_date, matter, (yea_votes > nay_votes), yea_votes, nay_votes, abs_votes)
                           bill.add_vote(vote)
                       
                       bill.add_action(chamber, matter, act_date)
             self.add_bill(bill)

    def scrape_bills(self,chamber,year):
        r = random.random()
        abbr = 'HB' if chamber == 'lower' else 'SB'
        year = int(year)
        if year not in self.internal_sessions:
            raise NoDataForYear(year)
        for session in self.internal_sessions[year]:
            #we *have* to refresh this page inbetween runs, otherwise the session will expire
            self.urlopen("http://alisondb.legislature.state.al.us/acas/ACASLoginMac.asp?SESSION=%s&C=%f" % (session[0], r))
            bill_id_int = 1
            while bill_id_int > 0:
                try:
                    current_bill = "%s%d" % (abbr, bill_id_int)
                    self.scrape_bill(chamber, current_bill, session)
                    bill_id_int += 1
                except Exception as e:
                    print e
                    break
        pass
    
    def dumber_vote(self, v):
        if v is None:
            return None
        else:
            return int(v)

    def dumb_vote(self, vote, name, t):
        if t == 'Y':
            vote.yes(name)
        elif t == 'N':
            vote.no(name)
        else:
	        vote.other(name)

    def scrape_metadata(self):
		#http://alisondb.legislature.state.al.us/acas/ACTIONSessionResultsFire.asp  -- sessions
		sessions = []
		session_details = {}
		
		with self.soup_context("http://alisondb.legislature.state.al.us/acas/ACTIONSessionResultsFire.asp") as session_page:
			#<option value="1051">Regular Session 2010</option>
			for option in session_page.find(id="Session").findAll('option'):
				year = int(re.findall(r'[0-9]+', option.string)[0]) #Regular Session 2010
				text = option.string.strip()
				if not year in self.internal_sessions:
					self.internal_sessions[year] = []
					session_details[year] = {'years': year, 'sub_sessions':[] }
					sessions.append(year)
				session_details[year]['sub_sessions'].append(text)
				self.internal_sessions[year].append([option['value'], text])
		return {
	        'state_name': 'Alabama',
	        'legislature_name': 'Alabama Legislature',
	        'lower_chamber_name': 'House of Representatives',
	        'upper_chamber_name': 'Senate',
	        'lower_title': 'Representative',
	        'upper_title': 'Senator',
	        'lower_term': 4,
	        'upper_term': 4,
	        'sessions': sessions,
	        'session_details': session_details
	    }
    def unescape(self,s):
		return re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), s)
		
if __name__ == '__main__':
    ALLegislationScraper().run()
