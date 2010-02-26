#!/usr/bin/env python
import sys
import os
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)

import legislators, bills, votes

from util import standardize_chamber

class ILLegislationScraper(LegislationScraper):

    state = 'il'

    metadata = {
        'state_name': 'Illinois',
        'legislature_name': 'The Illinois General Assembly',
        'lower_chamber_name': 'House of Representatives',
        'upper_chamber_name': 'Senate',
        'lower_title': 'Representative',
        'upper_title': 'Senator',
        'lower_term': 2,
        'upper_term': 4, # technically, in every decennial period, one 
                         # senatorial term is only 2 years. See 
                         # Article IV, Section 2(a) for more information.
        'sessions': ['93','94','95','96'],
        'session_details': {
            '93': {'years': [2003, 2004], 'sub_sessions': [
                'First Special Session', 'Second Special Session', 'Third Special Session', 
                'Fourth Special Session', 'Fifth Special Session', 'Sixth Special Session', 
                'Seventh Special Session', 'Eighth Special Session', 'Ninth Special Session', 
                'Tenth Special Session', 'Eleventh Special Session', 
                'Twelfth Special Session', 'Thirteenth Special Session', 
                'Fourteenth Special Session', 'Fifteenth Special Session', 
                'Sixteenth Special Session', 'Seventeenth Special Session', 
            ]},
            '94': {'years': [2005, 2006], 'sub_sessions': []},
            '95': {'years': [2007, 2008], 'sub_sessions': [
                'First Special Session', 'Second Special Session', 'Third Special Session', 
                'Fourth Special Session', 'Fifth Special Session', 'Sixth Special Session', 
                'Seventh Special Session', 'Eighth Special Session', 'Ninth Special Session', 
                'Tenth Special Session', 'Eleventh Special Session', 
                'Twelfth Special Session', 'Thirteenth Special Session', 
                'Fourteenth Special Session', 'Fifteenth Special Session', 
                'Sixteenth Special Session', 'Seventeenth Special Session', 
                'Eighteenth Special Session', 'Nineteenth Special Session', 
                'Twentieth Special Session', 'Twenty-First Special Session', 
                'Twenty-Second Special Session', 'Twenty-Third Special Session',
                'Twenty-Fourth Special Session', 'Twenty-Fifth Special Session',
                'Twenty-Sixth Special Session', 
            ]},
            '96': {'years': [2009, 2010], 'sub_sessions': [
                'First Special Session', 
            ]},
        }}

    def __init__(self, **kwargs):
        super(ILLegislationScraper, self).__init__(**kwargs)
        self.year2session = {}
        for session,details in self.metadata['session_details'].items():
            for year in details['years']:
                self.year2session[year] = session
                self.year2session[str(year)] = session


    def scrape_legislators(self, chamber, year):
        # Data available for 1993 on
        self.log("scrape legislators [chamber: %s] [year: %s]" % (chamber,year))
        try:
            session = self.year2session[year]
        except KeyError:                
            raise NoDataForYear(year)

        url = legislators.get_legislator_url(chamber,session)
        self.log("url: %s" % url)
        data = self.urlopen(url)

        for legislator in legislators.get_legislators(chamber,session,data):
            self.log("adding %s" % legislator['full_name'])        
            self.add_legislator(legislator)

    def scrape_bills(self, chamber, year):
        self.log("scrape legislators [chamber: %s] [year: %s]" % (chamber,year))
        try:
            session = self.year2session[year]
        except KeyError:                
            raise NoDataForYear(year)
        urls = bills.get_all_bill_urls(self, chamber,session,types=['HB','SB'])
        for url in urls:
            self._scrape_bill(url)

    def _scrape_bill(self,url):
        try:
            bill = bills.parse_bill(self, url)
            #self.apply_votes(bill)
            self.add_bill(bill)
            self.log("Added %s-%s" % (bill['session'],bill['bill_id']))
        except Exception, e:
            self.warning("Error parsing %s [%s] [%s]" % (url,e, type(e)))
        
    def apply_votes(self, bill):
        """Given a bill (and assuming it has a status_url in its dict), parse all of the votes
        """
        bill_votes = votes.all_votes_for_url(self, bill['status_url'])
        for (chamber,vote_desc,pdf_url,these_votes) in bill_votes:
            try:
                date = vote_desc.split("-")[-1]
            except IndexError:
                self.warning("[%s] Couldn't get date out of [%s]" % (bill['bill_id'],vote_desc))
                continue
            yes_votes = []
            no_votes = []
            other_votes = []
            for voter,vote in these_votes.iteritems():
                if vote == 'Y': 
                    yes_votes.append(voter)
                elif vote == 'N': 
                    no_votes.append(voter)
                else:
                    other_votes.append(voter)
            passed = len(yes_votes) > len(no_votes) # not necessarily correct, but not sure where else to get it. maybe from pdf
            vote = Vote(standardize_chamber(chamber),date,vote_desc,passed, len(yes_votes), len(no_votes), len(other_votes),pdf_url=pdf_url)
            for voter in yes_votes:
                vote.yes(voter)
            for voter in no_votes:
                vote.no(voter)
            for voter in other_votes:
                vote.other(voter)
            bill.add_vote(vote)

    def apply_votes_from_actions(self,bill):
        """Not quite clear on how to connect actions to vote PDFs, so this may not be usable.
        """
        for action_dict in bill['actions']:
            match = VOTE_ACTION_PATTERN.match(action_dict['action'])
            if match:
                motion,yes_count,no_count,other_count = match.groups()
                passed = int(yes_count) > int(no_count) # lame assumption - can we analyze the text instead?
                bill.add_vote(Vote(action_dict['actor'],action_dict['date'].strip(),motion.strip(),passed,int(yes_count),int(no_count),int(other_count)))


if __name__ == '__main__':
    ILLegislationScraper.run()
