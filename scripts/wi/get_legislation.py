#!/usr/bin/env python
import sys
sys.path.append('./scripts')
import datetime as dt, time
import re

from pyutils.legislation import LegislationScraper, NoDataForYear, ScrapeError, Legislator, Bill, Vote




class WisconsinScraper(LegislationScraper):
    state = 'wi'
    earliest_year = 1999
    internal_sessions = {}

    def scrape_metadata(self):
        sessions = []
        session_details = {}

        with self.soup_context("http://www.legis.state.wi.us/") as session_page:
            for option in session_page.find(id='session').findAll('option'):
                year = int(re.findall(r'[0-9]+', option.string)[0])
                text = option.string.strip()
                if not year in self.internal_sessions:
                    self.internal_sessions[year] = []
                    session_details[year] = {'years': [year], 'sub_sessions':[] }
                    sessions.append(year)
                session_details[year]['sub_sessions'].append(text)
                self.internal_sessions[year].append([option['value'], text])
        return {
            'state_name': 'Wisconsin',
            'legislature_name': 'Wisconsin State Legislature',
            'lower_chamber_name': 'Assembly',
            'upper_chamber_name': 'Senate',
            'lower_title': 'Representative',
            'upper_title': 'Senator',
            'lower_term': 2,
            'upper_term': 4,
            'sessions': sessions,
            'session_details': session_details
        }


if __name__ == '__main__':
    WisconsinScraper.run()