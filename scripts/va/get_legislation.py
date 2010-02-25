#!/usr/bin/env python
import re
import os
import sys
import datetime as dt
import time
import random
from BeautifulSoup import BeautifulSoup
from htmlentitydefs import name2codepoint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, NoDataForYear,
                                 Bill, Legislator, Vote)

class VANameMatcher:
    def wash(self, form):
        return form.replace('.', '').lower().strip()

    def __init__(self):
        self.names = {}

    def __setitem__(self, name, obj):
        forms = set()
        forms.add(name['full_name'])
        forms.add(name['last_name'])
        if len(name['middle_name']) > 0:
            forms.add("%s, %s%s" % (name['last_name'], name['first_name'][0], name['middle_name'][0]))
        else:
            forms.add("%s, %s" % (name['last_name'], name['first_name'][0]))

        for form in forms:
            form = self.wash(form)
            if form in self.names:
                self.names[form] = None
            else:
                self.names[form] = obj

    def __getitem__(self, name):
        name = self.wash(name)
        if name in self.names:
            return self.names[name]
        return None

class VALegislationScraper(LegislationScraper):
    state = 'va'
    internal_sessions = {}
    
    
    def scrape_legislators(self,chamber,year):
        #[session_id]/mbr/MBR.HTM
        abbr = {'upper': 'S', 'lower': 'H'}
        year = int(year)
        if year not in self.internal_sessions:
            raise NoDataForYear(year)
        for session in self.internal_sessions[year]:
            self.log(session[1])
            with self.soup_context("http://leg1.state.va.us/%s/mbr/MBR.HTM" % session[0]) as member_page:
                #<li><a href="/cgi-bin/legp504.exe?011+mbr+H102">L. Preston Bryant, Jr.</a>
                for member in member_page.findAll('a', href=re.compile("exe\?%s\+mbr\+%s" % (session[0], abbr[chamber]))):
                    self.fetch_member(member['href'], member.string, session[1], chamber)
        pass


    def fetch_member(self, url, name, session, chamber):
        abbr = {'R': 'Republican', 'D': 'Democrat', 'I': 'Independent'}
        url = "http://leg1.state.va.us/%s" % url
        with self.soup_context(url) as member:
            ex = member.findAll('table', text=re.compile(re.escape(name)))
            if ex == []:
                raise Exception("Parse error fetching member %s" % name)
            else:
                ex = ex[0].parent.nextSibling.nextSibling.string.split()

            # Some people are "Joe X. Schmoe;Resigned". Fantastic.
            name = re.split('\;|\(', name)[0]
            # some other people are Joe X. Schmoe (resigned
            name_parts = name.split()
            first_name = name_parts[0]
            last = name_parts[len(name_parts)-1]
            if re.match(r'[IV]+$|\bJr\b\.$|\b(Sr)\b\.$', last):
                last_name = name_parts[len(name_parts)-2]
            else:
                last_name = last
            
            if name_parts[1] == last_name:
                middle_name = ''
            else:
                middle_name = name_parts[1]

            # Deal with the Van Houtens of the world
            # also, watch out for their rugged Danish relatives...
            if name_parts[1] == 'Van':
                middle_name = ''
                last_name = name_parts[1] + ' ' + last_name

            last_name = last_name.replace(',','')

            middle_name = middle_name.replace('.', '')
            party = ex[0][1]
            district = ex[len(ex)-1]
	
            leg = Legislator(session=session, chamber=chamber, district=district, 
	                                           full_name=name.strip(), first_name=first_name.strip(), last_name=last_name.strip(), 
	                                           middle_name=middle_name.replace('.', '').strip(), party=abbr[party])
            leg.add_source(url)
            # [_,_,district,_]
            # so... yeah. not totally sure how I should handle legislators in subsessions
            # but I'll only add them if the matcher doesn't already know about them.
            sanitized = leg['full_name'].replace('.', '').lower()
            if self.matcher[chamber][sanitized] and self.matcher[chamber][sanitized][2] == district:
                return
            self.add_legislator(leg)

    def scrape_bills(self,chamber,year):
        #http://leg1.state.va.us/cgi-bin/legp504.exe?951+sum+HB246

        #http://leg1.state.va.us/cgi-bin/legp504.exe?943+mbr+HJ2026 HAHAHAHAHA
        #state governments are basically student councils?

        types = {'lower': ['HB', 'HJ'], 'upper': ['SB']} # we can add SR and HR if we want
        year = int(year)
        if year not in self.internal_sessions:
            raise NoDataForYear(year)

        for bill_type in types[chamber]:
            for session in self.internal_sessions[year]:
                bill_list = self.fetch_bill_list(session[0], bill_type)
                for abill in bill_list:
                    url = "http://leg1.state.va.us/cgi-bin/legp504.exe?%s+sum+%s" % (session[0], abill.replace(' ', ''))
                    with self.soup_context(url) as one_bill:
                        bill = Bill(session=session[1], chamber=chamber, bill_id=abill, title=bill_list[abill])
                        self.fetch_sponsors(bill, "http://leg1.state.va.us/cgi-bin/legp504.exe?%s+mbr+%s" % (session[0], abill.replace(' ', '')))
                        
                        summary_sections = str(one_bill).split('<font color="#FF6633">')
                        for chunk in summary_sections:
                            if chunk.startswith('<html>'):
                                continue
                            elif chunk.startswith("<i>Summary as passed"):
                                summary_passed = ' '.join(chunk.split('</b>')[1].split('\r\n'))
                            elif chunk.startswith("<i>Summary as introduced") or chunk.startswith('<i>Summary:'):
                                summary_introduced = ' '.join(chunk.split('</b>')[1].split('\r\n'))
                            elif chunk.startswith("<i>Full text"):
                                self.fetch_versions(bill, self.unescape(chunk))
                            elif chunk.startswith("<i>Amendments"):
                                self.fetch_amendments(bill, self.unescape(chunk)) 
                            elif chunk.startswith("<i>Status"):
                                self.fetch_actions(bill, one_bill)   
                            else:
                                pass
                        self.add_bill(bill)
        pass

    def fetch_sponsors(self, bill, url):
        i = 0
        c = ['upper','lower'] if bill['chamber'] == 'upper' else ['lower','upper']
        # this page is a 4 column table with 2 ULs. The first is always primary sponsors.
        with self.soup_context(url) as sponsors:
            for sponsors in sponsors.findAll('ul'):
                for rep in sponsors.findAll('li'):
                    p = rep.a.b.contents[0] if rep.a.b else rep.a.contents[0]
                    bill.add_sponsor(['sponsor', 'cosponsor'][i], p.strip(), chamber=c[i])
                i += 1

    def fetch_actions(self, bill, soup):
        abbr = {'Senate': 'upper', 'House': 'lower'}
        last_status = ''
        #this is a tricky one..
        soup = str(soup)
        fudged_status_blob = soup[soup.index('Status:'):].split('<br />')
        for line in fudged_status_blob:
            # <a href="/cgi-bin/legp504.exe?071+sub+H08002">02/06/07 &nbsp;House: Assigned Courts sub: Civil Law</a><br />
            line = self.unescape(line).strip()
            status = re.findall("(\d+/\d+\/\d+)\s+(\w+):\s+(.*)", line)
            if len(status) > 0:
                status = status[0]
                act_date = dt.datetime.strptime(status[0], '%M/%d/%y')
                if status[1] in abbr:
                    actor = abbr[status[1]]
                else:
                    actor = status[1]
                
                vote_check = BeautifulSoup(line).findAll('a', href=re.compile('\+vot\+'))
                if vote_check != []:
                    self.parse_vote(bill, actor, act_date, last_status, vote_check[0])

                clean_status = status[2].replace("</a>",'')
                bill.add_action(actor, clean_status, act_date)
                last_status = clean_status

    def parse_vote(self, bill, actor, date, text, line):
        url = "http://leg1.state.va.us%s" % line['href']
        abbr = {'S': 'upper', 'H': 'lower'}
        with self.soup_context(url) as vote_data:
            house = abbr[re.findall('\d+/\d+\/\d+\s+([\bHouse\b|\bSenate\b])', self.unescape(unicode(vote_data)))[0]]
            vote = Vote(house, date, text, None, 0, 0, 0)
            for cast in vote_data.findAll('p'):
                if cast.string is None:
                    continue
                cleaned = cast.string.replace('\r\n', ' ')
                split_start = cleaned.find('--')
                voted = cleaned[0:split_start].strip()
                split_end = cleaned.find('--', split_start + 2)
                if split_end == -1:
                    continue
                names = []
                maybe_names = cleaned[split_start+2:split_end].split(", ")
                t_name = ''
                #not sure how to skip iterations, so.
                for i in range(len(maybe_names)):
                   if re.match('\w\.\w\.', maybe_names[i]):
                       names.append(t_name + ', ' + maybe_names[i])
                       t_name = ''
                   else:
                       if t_name != '':
                           names.append(t_name)
                       t_name = maybe_names[i]
                for voter in names:
                    sanitized = voter.replace('.', '').lower()
                    if voted=='YEAS':
                        vote.yes(voter)
                    elif voted=='NAYS':
                        vote.no(voter)
                    else:
                        vote.other(voter.strip())
            vote['other_count'] = len(vote['other_votes'])			
            vote['yes_count'] = len(vote['yes_votes'])
            vote['no_count'] = len(vote['no_votes'])
            vote['passed'] = (vote['yes_count'] > vote['no_count'])
            bill.add_vote(vote)

    def fetch_amendments(self, bill, text):
        for link in BeautifulSoup(text).findAll('a'):
            bill.add_document(link.string, "http://leg1.state.va.us%s" % link['href'])

    def fetch_versions(self, bill, text):
        for link in BeautifulSoup(text).findAll('a'):
            if link['href'].endswith('pdf'):
                continue #skip it. (The very best thing of all! There's a counter on the ball!)
            elif link.b and "impact statement" in link.b.string:
                title = link.previousSibling
                if title['href'].endswith('pdf'):
                    title = re.findall("(\d+/\d+\/\d+)\s+(\w+):\s+(.*)", title.previousSibling.string)[0]
                bill.add_document('Impact Statement for "%s"' % title[2], "http://leg1.state.va.us%s" % link['href'])
            elif link.i:
                bill.add_document(link.i.string, "http://leg1.state.va.us%s" % link['href'])
            else:
                status = re.findall("(\d+/\d+\/\d+)\s+(\w+):\s+(.*)", link.string)[0]
                bill.add_version(status[2], "http://leg1.state.va.us%s" % link['href'], date=dt.datetime.strptime(status[0], '%M/%d/%y'))

    def fetch_bill_list(self, session, bill_type):
        internal_bills = {}
        start = ''
        #
        while True:
            with self.soup_context("http://leg1.state.va.us/cgi-bin/legp504.exe?ses=%s&typ=bil&val=%s*%s" % (session,bill_type,start)) as partial:
                #/cgi-bin/legp504.exe?001+sum+HB52
                bills = partial.findAll('a', href=re.compile('\/cgi-bin/legp504.exe\?%s\+sum\+%s([\d]+)' % (session, bill_type)))
                for bill in bills:
                    internal_bills[bill.string.strip()] = bill.nextSibling.string.strip()

                #get the next offset or return the list that we have
                next = partial.findAll('a', href=re.compile('\/cgi-bin/legp504.exe\?%s\+bil\+%s\*([\+\w\d]+)' % (session, bill_type)))
                if len(next) > 0:
                    start = re.findall(r'\/cgi-bin/legp504.exe\?%s\+bil\+%s\*([\+\w\d]+)' % (session, bill_type), next[0]['href'])[0]
                else:
                    return internal_bills                

    def scrape_metadata(self):
        if not self.sleep:
            raise Exception("You WILL get a temporary IP ban unless you use -s")
        sessions = []
        session_details = {}

        with self.soup_context("http://leg1.state.va.us/") as session_page:
            #<a href="/942/lis.htm">1994</a> <font face="arial" size=2>Special I<br>
            #this html is a mess, but the text is consistent.. soooo....
            titles = ['', 'Special Session I', 'Special Session II', 'Special Session III']
            for ech in session_page.findAll('a', href=re.compile('([\d+])\/lis.htm')):
                year = int(ech.string)
                if not year in self.internal_sessions:
                    self.internal_sessions[year] = []
                    session_details[ech.string] = {'years': [year], 'sub_sessions':[] }
                    sessions.append(ech.string)
                c = len(session_details[ech.string]['sub_sessions'])
                title = titles[c]
                if title:
                    session_details[ech.string]['sub_sessions'].append(title)
                    self.internal_sessions[year].append((re.findall(r'[0-9]+', ech['href'])[0], "%d %s" % (year, title)))
                else:
                    self.internal_sessions[year].append((re.findall(r'[0-9]+', ech['href'])[0], ech.string))

        return {
            'state_name': 'Virginia',
            'legislature_name': 'Virginia General Assembly',
            'lower_chamber_name': 'House of Delegates',
            'upper_chamber_name': 'Senate',
            'lower_title': 'Delegate',
            'upper_title': 'Senator',
            'lower_term': 4,
            'upper_term': 4,
            'sessions': sessions,
            'session_details': session_details
        }    

    def unescape(self,s):
        # I'd never actually seen a \xa0 in the wild before, but it breaks regexes and splits in crazy ways
        # that took me AGES to track down
        return s.replace('&nbsp;', ' ')

if __name__ == '__main__':
    VALegislationScraper.run(matcher={'upper': VANameMatcher, 'lower': VANameMatcher})
