#!/usr/bin/env python
from __future__ import with_statement
import re
import urllib
import urlparse
from BeautifulSoup import BeautifulSoup
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)

# URL for searching the Minnesota Legislature bills.
# The search form accepts number ranges for bill numbers.
# The following query params should be substituted in this URL:
#   'body=%s' = "House" or "Senate"
#   'session=%s' = legislative session. (See the 'year_mapping' data structure
#                  later in this file)
#   'bill=%s-%s' = Range Format: start-end (e.g. 1-10)
BILL_SEARCH_URL = 'https://www.revisor.leg.state.mn.us/revisor/pages/search_status/status_results.php?body=%s&search=basic&session=%s&bill=%s-%s&bill_type=bill&submit_bill=GO&keyword_type=all=1&keyword_field_long=1&keyword_field_title=1&titleword='

# Base URL for the details of a given bill.
BILL_DETAIL_URL_BASE = 'https://www.revisor.leg.state.mn.us/revisor/pages/search_status/'

# The versions of a bill use a different base URL.
VERSION_URL_BASE = "https://www.revisor.mn.gov"

class MNLegislationScraper(LegislationScraper):
    state = 'mn'

    def cleanup_text(self, text):
        '''Remove junk from text that MN puts in for formatting their tables.
        Removes surrounding whitespace.
        Replaces any '&nbsp;' chars with spaces.

        Returns a string with the problem text removed/replaced.
        '''
        # coerce to string...
        text = str(text)
        self.debug("Cleaning text: %s" % text)
        cleaned_text = text.replace('&nbsp;', '').strip()
        self.debug("Cleaned text: %s" % cleaned_text)
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
            self.debug("Found bill ID: %s" % bill_id)
        return bill_id

    def extract_bill_title(self, soup):
        '''Extract the title of a bill from a Bill Status page.'''
        # The bill title is in a table that has an attribute 'summary'
        # with a value of 'Short Description'.
        short_summary_table = soup.find('table', attrs={"summary" : "Short Description"})
        # The 'Short Summary' table has only one <td> which contains the
        # bill title inside a <font> element.
        bill_title = short_summary_table.td.font.contents[0]
        self.debug("Found Bill Title: %s" % bill_title)
        return bill_title

    def extract_senate_bill_version_link(self, soup):
        '''Extract the link which points to the version information for a
        given bill.
        '''
        # The "Bill Text" link for the Senate points you to a page of the
        # current draft of the bill.  At the top of this page there is a table
        # containing links for "Authors and Status", "List Versions", and a
        # PDF file for the bill. This method retreives the 'href' attribute
        # for the "List Versions" link.
        table = soup.find('table', attrs={"summary" : ""})
        rows = table.findAll("td")
        version_link = rows[2]
        bill_version_link = version_link.a.attrs[0][1]
        self.debug("Found Bill Version Link: %s" % bill_version_link)
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
        self.debug("Found Bill Versions: %d" % len(bill_versions))
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
        self.debug("Sponsors Found for this bill: %d" % len(bill_sponsors))
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
        self.debug("Actions Found for this bill: %d" % len(bill_actions))
        return bill_actions

    def get_bill_info(self, chamber, session, bill_detail_url, version_list_url):
	"""Extracts all the requested info for a given bill.

	Calls the parent's methods to enter the results into JSON files.
	"""
        if chamber == "House":
            chamber = 'lower'
        else:
            chamber = 'upper'

        with self.soup_context(bill_detail_url) as bill_soup:

            bill_id = self.extract_bill_id(bill_soup)
            bill_title =  self.extract_bill_title(bill_soup)
            bill = Bill(session, chamber, bill_id, bill_title)

        # Get all versions of the bill.
        # Versions of a bill are on a separate page, linked to from the column
        # labeled, "Bill Text", on the search results page.

        with self.soup_context(version_list_url) as version_soup:

            # MN bills can have multiple versions.  Get them all, and loop over
            # the results, adding each one.
            self.debug("Extracting bill versions from: " + version_list_url)
            bill_versions = self.extract_bill_versions(version_soup)
            for version in bill_versions:
                version_name = version['name']
                version_url = urlparse.urljoin(VERSION_URL_BASE, version['url'])
                bill.add_version(version_name, version_url)

            # grab primary and cosponsors
            # MN uses "Primary Author" to name a bill's primary sponsor.
            # Everyone else listed will be added as a 'cosponsor'.
            sponsors = self.extract_bill_sponsors(bill_soup)
            primary_sponsor = sponsors[0]
            cosponsors = sponsors[1:]
            bill.add_sponsor('primary', primary_sponsor)
            for leg in cosponsors:
                bill.add_sponsor('cosponsor', leg)

            # Add Actions performed on the bill.
            bill_actions = self.extract_bill_actions(bill_soup, chamber)
            for action in bill_actions:
                action_chamber = action['action_chamber']
                action_date = action['action_date']
                action_text = action['action_text']
                bill.add_action(action_chamber, action_text, action_date)

        self.add_bill(bill)

    def scrape_session(self, chamber, session, session_year, session_number, legislative_session):
        """Scrape all bills for a given chamber and a given session.

        This method uses the legislature's search page to collect all the bills
        for a given chamber and session.
        """

        # MN bill search page returns a maximum of 999 search results.
        # To get around that, make multiple search requests and combine the results.
        # when setting the search_range, remember that 'range()' omits the last value.
        search_range = range(0,10000, 900)
        min = search_range[0]
        total_rows = list() # used to concatenate search results
        for max in search_range[1:]:
            # The search form accepts number ranges for bill numbers.
            # Range Format: start-end
            # Query Param: 'bill='
            url = BILL_SEARCH_URL % (chamber, session, min, max-1)
            self.debug("Getting bill data from: %s" % url)
            with self.soup_context(url) as soup:
                # Index into the table containing the bills .
                rows = soup.findAll('table')[6].findAll('tr')[1:]
                self.debug("Rows to process: %s" % str(len(rows)))
                # If there are no more results, then we've reached the
                # total number of bills available for this session.
                if len(rows) == 0:
                    self.debug("Total Bills Found: %d" % len(total_rows))
                    break
                else:
                    total_rows.extend(rows)
                # increment min for next loop so we don't get duplicates.
                min = max

        # Now that we have all the bills for a given session, process each row
        # of search results to harvest the details and versions of each bill.
        for row in total_rows:
            # The second column of the row contains a link pointing to
            # the status page for the bill.
            # The fourth column of the row contains a link labeled, "Bill Text",
            # pointing to a list of versions of the bill.
            cols = row.findAll('td')
            bill_details_column = cols[1]
            bill_versions_column = cols[3]
            try:
                # Extract the 'href' attribute value.
                bill_details_url = bill_details_column.a.attrs[0][1]
                bill_details_url = urlparse.urljoin(BILL_DETAIL_URL_BASE, bill_details_url)
            except:
                self.warning('Bad bill_details_column: %s' % bill_details_column)
                continue
            try:
                # Extract the 'href' attribute value.
                bill_version_list_url = bill_versions_column.a.attrs[0][1]
            except:
                self.warning('Bad bill_versions_column: %s' % bill_versions_column)
                continue
            # Alas, the House and the Senate do not link to the same place for
            # a given bill's "Bill Text".  Getting a URL to the list of bill
            # versions from the Senate requires an extra step here.
            if chamber == 'Senate':
                senate_bill_text_url = urlparse.urljoin(VERSION_URL_BASE, bill_version_list_url)
                with self.soup_context(senate_bill_text_url) as senate_soup:
                    bill_version_list_url = self.extract_senate_bill_version_link(senate_soup)
            bill_version_list_url = urlparse.urljoin(VERSION_URL_BASE, bill_version_list_url)
            self.get_bill_info(chamber, session, bill_details_url, bill_version_list_url)

    def scrape_bills(self, chamber, year):
        """Initiates the scraping of all bills for a given chamber and year."""

        # Minnesota legislative session value formula
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
            self.debug("Scraping data for MN - Session: %s, Chamber: %s, Year: %s" % (session, chamber, year))
            self.scrape_session(chamber, session, session_year, session_number, legislative_session)

if __name__ == '__main__':
    MNLegislationScraper.run()
