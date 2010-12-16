import re
import datetime
import urlparse
from BeautifulSoup import BeautifulSoup
import lxml.html

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill

# Base URL for the details of a given bill.
BILL_DETAIL_URL_BASE = 'https://www.revisor.mn.gov/revisor/pages/search_status/'

# The versions of a bill use a different base URL.
VERSION_URL_BASE = "https://www.revisor.mn.gov"

class MNBillScraper(BillScraper):
    state = 'mn'

    def extract_senate_bill_version_link(self, soup):
        """Extract the link which points to the version information for a
        given bill.
        """
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

    def extract_bill_actions(self, doc, current_chamber):
        """Extract the actions taken on a bill.
        A bill can have actions taken from either chamber.  The current
        chamber's actions will be the first table of actions. The other
        chamber's actions will be in the second table.

        Returns a list of bill actions. Each bill action is a dict with keys:
            action_chamber = 'upper|lower'
            action = string
            date = MM/DD/YYYY
        """

        bill_actions = list()
        action_tables = doc.xpath('//table[@summary="Actions"]')

        for cur_table in action_tables:
            for row in cur_table.xpath('tr')[1:]:
                bill_action = dict()

                # split up columns
                (date_col, action_col, desc_col, text_col,
                 page_col, rc_col) = row.xpath('td')

                action_date = date_col.text_content().strip()
                action_text = action_col.text_content().strip()
                description = desc_col.text_content().strip()

                # skip non-actions (don't have date)
                if action_text in ('Chapter number', 'See also', 'See',
                                   'Effective date', 'Secretary of State'):
                    continue

                try:
                    action_date = datetime.datetime.strptime(action_date,
                                                             '%m/%d/%Y')
                except ValueError:
                    try:
                        action_date = datetime.datetime.strptime(description,
                                                                 '%m/%d/%y')
                    except ValueError:
                        self.warning('ACTION without date: %s' % action_text)
                        continue

                bill_action['action_text'] = action_text
                if description:
                    action_text += ' ' + description
                bill_action['action_chamber'] = current_chamber
                bill_action['action_date'] = action_date
                bill_actions.append(bill_action)

            # if there's a second table, toggle the current chamber
            if current_chamber == 'upper':
                current_chamber = 'lower'
            else:
                current_chamber = 'upper'

        return bill_actions

    def get_bill_info(self, chamber, session, bill_detail_url, version_list_url):
        """Extracts all the requested info for a given bill.

        Calls the parent's methods to enter the results into JSON files.
        """
        if chamber == "House":
            chamber = 'lower'
        else:
            chamber = 'upper'

        with self.urlopen(bill_detail_url) as bill_html:
            doc = lxml.html.fromstring(bill_html)

            bill_id = doc.xpath('//title/text()')[0].split()[0]
            bill_title = doc.xpath('//font[@size=-1]/text()')[0]
            bill = Bill(session, chamber, bill_id, bill_title)
            bill.add_source(bill_detail_url)

            # grab sponsors
            # TODO: determine if first is always the sole primary sponsor?
            sponsors = doc.xpath('//table[@summary="Show Authors"]/descendant::a/text()')
            if sponsors:
                primary_sponsor = sponsors[0].strip()
                bill.add_sponsor('primary', primary_sponsor)
                cosponsors = sponsors[1:]
                for leg in cosponsors:
                    bill.add_sponsor('cosponsor', leg.strip())

            # Add Actions performed on the bill.
            bill_actions = self.extract_bill_actions(doc, chamber)
            for action in bill_actions:
                bill.add_action(action['action_chamber'],
                                action['action_text'],
                                action['action_date'])

        # Get all versions of the bill.
        # Versions of a bill are on a separate page, linked to from the column
        # labeled, "Bill Text", on the search results page.
        with self.urlopen(version_list_url) as version_html:
            version_doc = lxml.html.fromstring(version_html)
            for v in doc.xpath('//a[starts-with(@href, "/bin/getbill.php")]'):
                version_url = urlparse.urljoin(VERSION_URL_BASE, v.get('href'))
                bill.add_version(v.text.strip(), version_url)

        self.save_bill(bill)

    def scrape(self, chamber, session):
        """Scrape all bills for a given chamber and a given session.

        This method uses the legislature's search page to collect all the bills
        for a given chamber and session.
        """
        search_chamber = {'lower':'House', 'upper':'Senate'}[chamber]
        search_session = self.metadata['session_details'][session]['site_id']

        # MN bill search page returns a maximum of 999 search results.
        # To get around that, make multiple search requests and combine the results.
        # when setting the search_range, remember that 'range()' omits the last value.
        total_rows = list() # used to concatenate search results
        stride = 900
        start = 0
        for start in xrange(0, 10000, stride):
            # body: "House" or "Senate"
            # session: legislative session id
            # bill: Range start-end (e.g. 1-10)
            url = 'https://www.revisor.mn.gov/revisor/pages/search_status/status_results.php?body=%s&session=%s&bill=%s-%s&bill_type=bill&submit_bill=GO' % (search_chamber, search_session, start, start+stride)

            with self.urlopen(url) as html:
                soup = BeautifulSoup(html)
                # Index into the table containing the bills .
                rows = soup.findAll('table')[6].findAll('tr')[1:]
                # If there are no more results, then we've reached the
                # total number of bills available for this session.
                if len(rows) == 0:
                    self.debug("Total Bills Found: %d" % len(total_rows))
                    break
                else:
                    total_rows.extend(rows)

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
            if search_chamber == 'Senate':
                senate_bill_text_url = urlparse.urljoin(VERSION_URL_BASE, bill_version_list_url)
                with self.urlopen(senate_bill_text_url) as senate_html:
                    senate_soup = BeautifulSoup(senate_html)
                    bill_version_list_url = self.extract_senate_bill_version_link(senate_soup)
            bill_version_list_url = urlparse.urljoin(VERSION_URL_BASE, bill_version_list_url)
            self.get_bill_info(search_chamber, session, bill_details_url, bill_version_list_url)
