#!/usr/bin/env python

import re
import urllib
import urlparse
from BeautifulSoup import BeautifulSoup
from mechanize import Browser
import logging

# Toggle this to the logging verbosity you want.
verbosity = logging.DEBUG

logger = logging.getLogger("MNScraper")
logger.setLevel(verbosity)
console_handler = logging.StreamHandler()
# Set up log formatters, and add them to the handlers.
console_formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(console_formatter)
# Add the handlers to the logger.
logger.addHandler(console_handler)




# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class MNLegislationScraper(LegislationScraper):
    '''
    The following are functions that you can call on to store your data. The **kwargs argument is options but it allows you to define your own fields to populate.

        * add_bill(bill_chamber,bill_session,bill_id,bill_name, **kwargs)
              * bill_chamber: Whichever chamber the bill game from, either "upper" or "lower". [What do we do when there is only one chamber?]
              * bill_session: Session number bill came from, as defined by the state, be that 2007, or 196, or Whatever.
              * 'bill_id: However the state identifies the bill. For example: S-102,H42.
              * bill_name: The English name the stage gave the bill 
        * add_bill_version(bill_chamber,bill_session,bill_id,version_name, version_url, **kwargs)
              * bill_chamber same as in add_bill
              * bill_session same as in add_bill
              * bill_id same as in add_bill
              * version_name Name of version, whatever the state named it. This could be "Committee Draft", "Proposed Version". If there is only one version of the bill, you can just say "Full Text".
              * version_url Full url to full text of bill (HTML and plan text preferred, but get whatever type of document you can) 
        * add_sponsorship(self, bill_chamber, bill_session, bill_id, sponsor_type, sponsor_name, **kwargs)
              * bill_chamber same as in add_bill
              * bill_session same as in add_bill
              * bill_id same as in add_bill
              * sponsor_type The type of the sponsorship "primary", "secondary", etc.
              * sponsor_name The name of the entity that is sponsoring the bill, be that a person or a committee, or something else. 
        * add_action(bill_chamber, bill_session, bill_id, action_chamber, action_text, action_date, **kwargs)
              * bill_chamber same as in add_bill
              * bill_session same as in add_bill
              * bill_id same as in add_bill
              * action_chamber Chamber in which action happened. [What if it happened outside of either chamber?]
              * action_text Whatever the state called the action
              * action_date date/time action happened [Should we standardize the format?] 
    '''

    state = 'mn'

    def cleanup_text(self, text):
        '''Remove junk from text that MN puts in for formatting their tables.
        Removes surrounding whitespace. 
        Replaces any '&nbsp;' chars with spaces.
        
        Returns a string with the problem text removed/replaced.
        '''
        # coerce to string...
        text = str(text)
        logger.debug("Cleaning text: %s", text)
        cleaned_text = text.replace('&nbsp;', '').strip()
        logger.debug("Cleaned text: %s", cleaned_text)
        return cleaned_text

    def extract_bill_id(self, soup):
        '''Extract the ID of a bill from a Bill Status page.'''
        # The bill name is in a table that has an attribute 'summary' 
        # with a value of 'Show Doc Names'.
        doc_name_table = soup.find('table', attrs={"summary" : "Show Doc Names"})
        bill_id_raw = doc_name_table.td.contents[0]
        bill_id = re.search(r'Bill Name:\s+([H|S]F\d+)', bill_id_raw)
        if bill_id is not None:
            bill_id = bill_id.groups()[0]
            logger.debug("Found bill ID: %s", bill_id)
        return bill_id

    def extract_bill_title(self, soup):
        '''Extract the title of a bill from a Bill Status page.'''
        # The bill title is in a table that has an attribute 'summary'
        # with a value of 'Short Description'.
        short_summary_table = soup.find('table', attrs={"summary" : "Short Description"})
        # The 'Short Summary' table has only one <td> which contains the 
        # bill title inside a <font> element.
        bill_title = short_summary_table.td.font.contents[0]
        logger.debug("Found Bill Title: %s", bill_title)
        return bill_title

    def extract_bill_version_link(self, soup):
        '''Extract the link which points to the version information for a 
        given bill.
        '''
        doc_name_table = soup.find('table', attrs={"summary" : "Show Doc Names"})
        bill_version_raw = doc_name_table.td
        bill_version_link = bill_version_raw.a.attrs[0][1]
        logger.debug("Found Bill Version Link: %s", bill_version_link)
        return bill_version_link

    def extract_bill_versions(self, soup):
        '''Extract all versions of a given bill.

        Returns a list of dicts with 'name' and 'url' keys for each version
        found.
        '''
        bill_versions = list()
        # A table of all versions of a bill exists in a table
        # which has a 'summary' attribute with a value of ''.
        versions_table = soup.find('table', attrs={'summary' : ''})
        table_rows = versions_table.findAll('tr')
        for row in table_rows:
            cols = row.findAll('td')
            # if the row has more than one column of info, then there's a bill version 
            # in there.
            if len(cols) > 1:
                # The version_name and version_url we are looking for are in the 
                # first column of the table.
                bill_version = dict()
                bill_version_column = cols[0]
                bill_version['name'] = self.cleanup_text(bill_version_column.a.contents[0])
                bill_version['url'] = bill_version_column.a.attrs[0][1]
                bill_versions.append(bill_version)
                del bill_version
        logger.debug("Found Bill Versions: %d", len(bill_versions))
        return bill_versions

    def extract_bill_sponsors(self, soup):
        '''Extract the primary and cosponsors for a given bill.'''
        bill_sponsors = list()
        sponsors_table = soup.find('table', attrs={'summary' : 'Show Authors'})
        # Sponsors' names are links within the sponsors_table table.
        sponsors_links = sponsors_table.findAll('a')
        for link in sponsors_links:
            sponsor_name = link.contents[0]
            bill_sponsors.append(sponsor_name)
        logger.debug("Sponsors Found for this bill: %d", len(bill_sponsors))
        return bill_sponsors

    def extract_bill_actions(self, soup, current_chamber):
        '''Extract the actions taken on a bill.
        A bill can have actions taken from either chamber.  The current
        chamber's actions will be the first table of actions. The other
        chamber's actions will be in the second table.

        Returns a list of bill actions. Each bill action is a dict with keys:
            action_chamber = 'upper|lower'
            action = string
            date = MM/DD/YYYY
        '''
        bill_actions = list()
        action_tables = soup.findAll('table', attrs={'summary' : 'Actions'})
        # First, process the actions taken by the current chamber.
        current_chamber_action_table = action_tables[0]
        current_chamber_action_rows = current_chamber_action_table.findAll('tr')
        for row in current_chamber_action_rows[1:]:
            bill_action = dict()
            cols = row.findAll('td')
            action_date = self.cleanup_text(cols[0].contents[0])
            action_text = self.cleanup_text(cols[1].contents[0])
            bill_action['action_date'] = action_date
            bill_action['action_text'] = action_text
            bill_action['action_chamber'] = current_chamber
            bill_actions.append(bill_action)

        # if there are more than one action_table, then the other chamber has
        # taken action on the bill.
        # Toggle the current chamber
        if current_chamber == 'upper':
            current_chamber = 'lower'
        else:
            current_chamber = 'upper'
        if len(action_tables) > 1:
            current_chamber_action_table = action_tables[1]
            current_chamber_action_rows = current_chamber_action_table.findAll('tr')
            for row in current_chamber_action_rows[1:]:
                bill_action = dict()
                cols = row.findAll('td')
                action_date = self.cleanup_text(cols[0].contents[0])
                action_text = self.cleanup_text(cols[1].contents[0])
                bill_action['action_date'] = action_date
                bill_action['action_text'] = action_text
                bill_action['action_chamber'] = current_chamber
                bill_actions.append(bill_action)
        logger.debug("Actions Found for this bill: %d", len(bill_actions))
        return bill_actions

    def get_bill_info(self, chamber, session, bill_detail_url):
        bill_detail_url_base='https://www.revisor.leg.state.mn.us/revisor/pages/search_status/'
        bill_detail_url = urlparse.urljoin(bill_detail_url_base, bill_detail_url)

        # parse the bill data page, finding the latest html text
        if chamber == "House":
            chamber = 'lower'
        else:
            chamber = 'upper'

        bill_data = urllib.urlopen(bill_detail_url).read()
        bill_soup = BeautifulSoup(bill_data)

        bill_id = self.extract_bill_id(bill_soup)
        bill_title =  self.extract_bill_title(bill_soup)
        self.add_bill(chamber, session, bill_id, bill_title)

        # get all versions
        # Versions of a bill are on a separate page, linked to from the bill
        # details page in a link titled, "Bill Text".
        version_url_base = 'https://www.revisor.leg.state.mn.us'
        bill_version_link = self.extract_bill_version_link(bill_soup)
        version_detail_url = urlparse.urljoin(version_url_base, bill_version_link)

        version_data = urllib.urlopen(version_detail_url).read()
        version_soup = BeautifulSoup(version_data)

        # MN bills can have multiple versions.  Get them all, and loop over
        # the results, adding each one.
        bill_versions = self.extract_bill_versions(version_soup)
        for version in bill_versions:
            version_name = version['name']
            version_url = urlparse.urljoin(version_url_base, version['url'])
            self.add_bill_version(chamber, session, bill_id, version_name, version_url)

        # grab primary and cosponsors 
        # MN uses "Primary Author" to name a bill's primary sponsor.
        # Everyone else listed will be added as a 'cosponsor'.
        sponsors = self.extract_bill_sponsors(bill_soup)
        primary_sponsor = sponsors[0]
        cosponsors = sponsors[1:]
        self.add_sponsorship(chamber, session, bill_id, 'primary', primary_sponsor)
        for leg in cosponsors:
            self.add_sponsorship(chamber, session, bill_id, 'cosponsor', leg)

        # Add Actions performed on the bill.
        bill_actions = self.extract_bill_actions(bill_soup, chamber)
        for action in bill_actions:
            action_chamber = action['action_chamber']
            action_date = action['action_date']
            action_text = action['action_text']
            self.add_action(chamber, session, bill_id, action_chamber, action_text, action_date)

    def scrape_session(self, chamber, session, session_year, session_number, legislative_session):

        # MN bill search page returns a maximum of 999 search results.
        # To get around that, make multiple search requests and combine the results.
        # when setting the search_range, remember that 'range()' omits the last value.
        search_range = range(0,10000, 500)
        min = search_range[0]
        for max in search_range[1:]:
            # The search form accepts number ranges for bill numbers.
            # Range Format: start-end
            # Query Param: 'bill='
            url = 'https://www.revisor.leg.state.mn.us/revisor/pages/search_status/status_results.php?body=%s&search=basic&session=%s&bill=%s-%s&bill_type=bill&submit_bill=GO&keyword_type=all=1&keyword_field_long=1&keyword_field_title=1&titleword=' % (chamber, session, min, max-1)
            logger.debug("Getting bill data from: %s", url)
            data = urllib.urlopen(url).read()
            soup = BeautifulSoup(data)
            total_rows = list() # used to concatenate search results
            # Index into the table containing the bills .
            rows = soup.findAll('table')[6].findAll('tr')[1:]
            logger.debug("Rows to process: %s", str(len(rows)))
            # If there are no more results, then we've reached the
            # total number of bills available for this session.
            if rows == []:
                return total_rows
            total_rows.extend(rows)
            # increment min for next loop so we don't get duplicates.
            min = max 
    
        for row in total_rows:
            # The second column of the row contains a link pointing to 
            # the status page for the bill.  We'll go there to extract all
            # the bill's info.
            cols = row.findAll('td')
            bill_details_column = cols[1]
            # Extract the 'href' attribute value.
            bill_details_url = bill_details_column.a.attrs[0][1]
            self.get_bill_info(chamber, session, bill_details_url)

    def scrape_bills(self, chamber, year):
        # Minnesota session value formula
        # 2009 = '0862009'
        # Bit       Value
        # ---       -----
        # 1         Session Number (session_number used in query params)
        # 2-4       Legislative Session (i.e. 86th session)
        # 4-8       YYYY four-digit year of the legislative session.
        year_mapping = {
            '1995': ('1791995',),
            '1996': ('0791995',),
            '1997': ('1801997', '2801997', '3801997'),
            '1998': ('1801998', '0801997'),
            '1999': ('0811999',),
            '2000': ('0811999',),
            '2001': ('0822001', '1822001'),
            '2002': ('0822001', '1822002'),
            '2003': ('0832003', '1832003'),
            '2004': ('0832003',),
            '2005': ('0842005',),
            '2006': ('0842005',),
            '2007': ('0852007', '1852007'),
            '2008': ('0852007',),
            '2009': ('0862009',),
        }
        available_chambers = {'lower':'House', 'upper':'Senate'}
        chamber = available_chambers[chamber]

        if year not in year_mapping:
            raise NoDataForYear(year)

        for session in year_mapping[year]:
            session_year = year
            # Unpacking MN session formula described above.
            session_number = session[0]
            legislative_session = session[1:3]
            legislative_session_year = session[-4:]
            logger.debug("Scraping data for MN - Session: %s, Chamber: %s, Year: %s", session, chamber, year)
            self.scrape_session(chamber, session, session_year, session_number, legislative_session)

if __name__ == '__main__':
    MNLegislationScraper().run()
#chamber, session, session_year, session_number, legislative_session
#    MNLegislationScraper().scrape_session('House', '0862009', '2009', '0', '86' )
