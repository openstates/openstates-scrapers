#!/usr/bin/env python
import re
import os
import sys
import datetime as dt, time
import random
import html5lib
from htmlentitydefs import name2codepoint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, NoDataForYear,
                                 Bill, Legislator, Vote)

class LANameMatcher:
    def wash(self, form):
        return form.replace('.', '').lower().strip()

    def __init__(self):
        self.names = {}

    def __setitem__(self, name, obj):
        forms = set()
        forms.add(name['full_name'])

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

class LouisianaScraper(LegislationScraper):
    #must set state attribute as the state's abbreviated name
    state = 'la'
    internal_sessions = {}

    soup_parser =  html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse
    
    def scrape_legislators(self,chamber,year):
        year = int(year)
        # we can scrape past legislator's from the main session page,
        # but we don't know what party they were..
        #http://house.louisiana.gov/H_Reps/members.asp?ID=
        #http://senate.legis.state.la.us/Senators/ByDistrict.asp
        if year != dt.date.today().year:
            raise NoDataForYear(year)
        if chamber == 'upper':
            self.scrape_upper_house(year)
        else:
            self.scrape_lower_house(year)
        pass

    def scrape_upper_house(self, year):
        with self.soup_context('http://senate.legis.state.la.us/Senators/ByDistrict.asp') as senator_page:
            for senator in senator_page.findAll('td', width=355)[0].findAll('tr'):
                link = senator.findAll('a', text=re.compile("Senator"))
                if link != []:
                    with self.urlopen_context('http://senate.legis.state.la.us%s' % link[0].parent['href']) as legislator_text:
                        legislator = self.soup_parser(legislator_text)
                        aleg = self.unescape(unicode(legislator))
                        #Senator A.G.  Crowe &nbsp; -&nbsp; District 1
                        name = re.findall(r'Senator ([\w\s\.\,\"\-]+)\s*\-\s*District', aleg)[0].strip()
                        name = name.replace('  ', ' ')
                        district = re.findall(r'\s*District (\d+)', aleg)[0]
                        """<b>Party</b><br>
                                Republican <br>"""
                        party = re.findall(r'<b>Party<\/b><br \/>\s*(\w+)\s*<', aleg)
                        first, middle, last, suffix = self.parse_name(name)
                        leg = Legislator(str(year), 'upper', str(district), name, first, middle, last, party, suffix=suffix)
                        self.add_legislator(leg)

    def scrape_lower_house(self, year):
        #todo: tedious name parsing
        for i in range(1,106):
            with self.soup_context("http://house.louisiana.gov/H_Reps/members.asp?ID=%d" % i) as legislator:
                aleg = self.unescape(unicode(legislator))
                name = re.findall(r'Representative ([\w\s\.\,\"\-]+)\s*<br', aleg)[0].strip()
                party, district = re.findall(r'(\w+)\s*District\s*(\d+)', aleg)[0]
                first, middle, last, suffix = self.parse_name(name)
                leg = Legislator(str(year), 'lower', str(district), name, first, middle, last, party, suffix=suffix)
                
                self.add_legislator(leg)

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


    def scrape_bills(self,chamber,year):
        year = int(year)
        abbr = {'upper': 'sen', 'lower': 'hse'}
        for session in self.internal_sessions[year]:
            s_id = re.findall('\/(\w+)\.htm', session[0])[0]
            #"http://www.legis.state.la.us/bills/byinst.asp?sessionid=99RS&billtype=SB&billno=593"
            with self.soup_context('http://www.legis.state.la.us/archive/%s/bills%s.htm' % (s_id, abbr[chamber])) as bills:
                for bill in bills.findAll('a', href=re.compile('billtype=\w\w&billno=\d+')):
                    self.scrape_a_bill(bill['href'], chamber, session[1])
        #http://www.legis.state.la.us/archive/99rs/billssen.htm
        #http://www.legis.state.la.us/archive/99rs/billshse.htm

        #http://www.legis.state.la.us/bills/byinst.asp?sessionid=99RS&billtype=HB&billno=18
        pass

    def scrape_a_bill(self, bill, chamber, session_name):
        abbr = {'upper': 'SB', 'lower': 'HB'}
        bill_info = re.findall('sessionid=(\w+)&billtype=(\w+)&billno=(\d+)', bill)[0]
        with self.soup_context(bill) as bill_summary:
            title = unicode(bill_summary.findAll(text=re.compile('Summary'))[0].parent)
            title = title[(title.find('</b>')+5):-5]

        bill_id = "%s %s" % (bill_info[1], bill_info[2])
        the_bill = Bill(session_name, chamber, bill_id, title)
        versions = self.scrape_versions(the_bill, bill_info[0], bill_info[1], bill_info[2])
        history = self.scrape_history(the_bill, bill_info[0], bill_info[1], bill_info[2])
        # sponsor names are really different than what we pull off of the rosters.
        # thanks louisiana
        sponsors = self.scrape_sponsors(the_bill, bill_info[0], bill_info[1], bill_info[2])
        documents = self.scrape_docs(the_bill, bill_info[0], bill_info[1], bill_info[2])

        self.add_bill(the_bill)

    def scrape_docs(self, bill, session, chamber, bill_no):
        url = 'http://www.legis.state.la.us/billdata/byinst.asp?sessionid=%s&billid=%s%s&doctype=AMD' % (session, chamber, bill_no)
        bill.add_source(url)
        with self.soup_context(url) as docs:
            for doc in docs.findAll('table')[2].findAll('tr'):
                if not doc.td or not doc.td.a.string:
                    continue
                bill.add_document(doc.td.a.string, "http://www.legis.state.la.us/billdata/%s" % doc.td.a['href'])

    def scrape_versions(self, bill, session, chamber, bill_no):
        url = 'http://www.legis.state.la.us/billdata/byinst.asp?sessionid=%s&billid=%s%s&doctype=BT' % (session, chamber, bill_no)
        bill.add_source(url)
        with self.soup_context(url) as versions:
            for version in versions.findAll('table')[2].findAll('tr'):
                if version.td is None:
                    continue
                bill.add_version(version.td.a.string, "http://www.legis.state.la.us/billdata/%s" % version.td.a['href'])


    def scrape_history(self, bill, session, chamber, bill_no):
        abbr = {'S': 'upper', 'H': 'lower'}
        url = 'http://www.legis.state.la.us/billdata/History.asp?sessionid=%s&billid=%s%s' % (session, chamber, bill_no)
        bill.add_source(url)
        with self.soup_context(url) as history:
            for action in history.findAll('table')[2].findAll('tr'):
                (date, house, _, matter) = action.findAll('td')
                if date.b:
                    continue
                act_date = dt.datetime.strptime(date.string, "%m/%d/%Y")
                bill.add_action(abbr[house.string], matter.string, act_date)
    
    def scrape_sponsors(self, bill, session, chamber, bill_no):
        #http://www.legis.state.la.us/billdata/Authors.asp?sessionid=09RS&billid=SB1
        abbr = {'S': 'upper', 'H': 'lower'}
        url = 'http://www.legis.state.la.us/billdata/Authors.asp?sessionid=%s&billid=%s%s' % (session, chamber, bill_no)
 
        bill.add_source(url)
        with self.soup_context(url) as history:
            for sponsor in history.findAll('table')[2].findAll('tr'):
                name = sponsor.td.string
                t = ''
                if name is None:
                    continue
                elif name.count('(Primary Author)') > 0:
                    t = 'primary'
                    name = name.replace('(Primary Author)','')
                else:
                    t = 'cosponsor'
                bill.add_sponsor(t, name)

    def flatten(self, tree):
	    if tree.string:
	        s = tree.string
	    else:
	        s = map(lambda x: self.flatten(x), tree.contents)
	        if len(s) == 1:
	            s = s[0]
	    return s

    def scrape_metadata(self):
        # http://www.legis.state.la.us/session.htm
        sessions = []
        session_details = {}
        with self.soup_context("http://www.legis.state.la.us/session.htm") as session_page:
            for session in session_page.findAll('a'):
                if session.strong == None:
                    continue
                tmp =  re.split(r'\s*', ''.join(self.flatten(session.strong)))
                text = ' '.join(map(lambda x: x.strip(), tmp))
                year = int(re.findall(r'^[0-9]+', text)[0])
                if not year in self.internal_sessions:
                    self.internal_sessions[year] = []
                    session_details[year] = {'years': [year], 'sub_sessions':[] }
                    sessions.append(str(year))

                if text.endswith('Regular Legislative Session'):
                    text = str(year)
                else:
                    session_details[year]['sub_sessions'].append(text)

                self.internal_sessions[year].append((session['href'], text))

            return {
                'state_name': 'Louisiana',
                'legislature_name': 'Louisiana Legislature',
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
        return re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), s).encode('ascii', 'ignore')

if __name__ == '__main__':
    LouisianaScraper.run({'upper': LANameMatcher, 'lower': LANameMatcher})
