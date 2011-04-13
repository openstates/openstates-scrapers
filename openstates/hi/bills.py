from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from openstates.hi import metadata

import lxml.html
from datetime import datetime
import os

from utils import STATE_URL, house, chamber_label # Data structures.
from utils import get_session_details, get_chamber_string # Functions.

class HIBillScraper(BillScraper):
    state = 'hi'

    def __init__(self, *kwargs, **args):
        super(HIBillScraper, self).__init__(*kwargs, **args)
        """
        session_scraper dict associates urls with scrapers for types of
        session pages. BillScraper.scrape() uses this to find the
        approriate page url and scrape method to run for a specific
        chamber and session defined in module __init__.py.
        """
        self.session_scraper = {
            '2009 First Special Session': ["/splsession%s/", self.scrape_20091SS],
            '2009 Second Special Session': ["/splsession%sb/", self.scrape_20101SS],
            '2009 Third Special Session': ["/splsession%sc/", self.scrape_20101SS],
            '2010 First Special Session': ["/splsession%s/", self.scrape_20101SS],
            '2010 Second Special Session': ["/splsession%sb/", self.scrape_20101SS],
        }

    def scrape(self, chamber, session):
        self.validate_session(session) # Check session is defined in init file.
        # Work out appropriate scaper for year and session type.
        year_label, session_type = get_session_details(session)
        # Check if session scaper already implemented.
        url, scraper = self.session_scraper.get(session, [None, None])

        # Configure for general cases.
        if scraper is None:
            url = "/session%s/lists/RptIntro%s.aspx"
            scraper = self.scrape_regular

        scraper(chamber, session, STATE_URL+url)

    def scrape_regular(self, chamber, session, url):
        """Scraper for post 2009 Regular Sessions."""
        year_label, session_type = get_session_details(session)
        chamber_string = get_chamber_string(url, chamber)
        bill_list_url = url%(year_label, chamber_string)
        with self.urlopen(bill_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_list_url)
            table = page.xpath('//table[contains(@id, "ReportGridView")]')[0]
            for row in table.xpath('tr'):
                # import pdb; pdb.set_trace()
                self.scrape_regular_row(chamber, session, row)

    def scrape_regular_row(self, chamber, session, row):
        """Returns bill attributes from row."""
        params = {}
        params['session'] = session
        params['chamber'] = chamber

        b = row.xpath('td/font/a[contains(@id, "HyperLink1")]')
        if b: # Ignore if no match
            bill_status_url = b[0].attrib['href']
            bill_url = row.xpath('td/font/span[contains(@id, "_Label2")]')[0].text
            params['bill_id'] = b[0].xpath('font')[0].text
            params['title'] = row.xpath('td/font/span[contains(@id, "_Label1")]/u/font')[0].text
            subject = row.xpath('td/font/span[contains(@id, "_Label6")]')[0].text
            subject = subject.replace('RELATING TO ', '') # Remove lead text
            params['subjects'] = [subject.replace('.', '')]
            params['description'] = row.xpath('td/font/span[contains(@id, "_Label2")]')[0].text
            sponsors = row.xpath('td/font/span[contains(@id, "_Label7")]')[0].text
            params['companion'] = row.xpath('td/font/span[contains(@id, "_Label8")]')[0].text
            bill = Bill(**params)
            bill.add_sponsor('primary', sponsors)
            actions = self.scrape_actions(bill, bill_status_url)
            bill.add_source(bill_status_url)
            self.save_bill(bill)
        return

    def scrape_actions(self, bill, bill_url):
        """Scrapes the bill actions from the bill details page."""
        actions = []
        with self.urlopen(bill_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_url)
            table = page.xpath('//table[contains(@id, "GridView1")]')[0]
            for row in table.xpath('tr'):
                # import pdb; pdb.set_trace()
                action_params = {}
                cells = row.xpath('td')
                if len(cells) == 3:
                    ch = cells[1].xpath('font')[0].text
                    action_params['actor'] = house[ch]
                    action_params['action'] = cells[2].xpath('font')[0].text
                    action_date = cells[0].xpath('font')[0].text
                    action_params['date'] = datetime.strptime(action_date, "%m/%d/%Y")
                    actions.append(action_params)
            for action_params in actions:
                bill.add_action(**action_params)
            # Add version document if not on a javascript link.
            try:
                bill_version = page.xpath('//a[contains(@id, "HyperLinkPDF")]')[0].attrib['href']
                bill.add_version('Current version', bill_version)
            except IndexError: # href not found.
                pass
        return

    def scrape_regular_status_page(self, url, params={}):
        """Scrapes the status page url, populating parameter dict and
        returns bill
        """
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            params['title'] = page.xpath('//div[div[contains( \
                ., "Report Title")]]/div[contains(@class, "rightside")]')[0].text.strip()
            subject = page.xpath('//div[div[contains( \
                ., "Measure Title")]]/div[contains(@class, "rightside")]')[0].text.strip()
            sponsors = page.xpath('//div[div[contains( \
                ., "Introducer")]]/div[contains(@class, "rightside")]')[0].text.strip()
            subject = subject.replace('RELATING TO ', '') # Remove lead text
            params['subject'] = subject.replace('.', '')
            params['description'] = page.xpath('//div[div[contains( \
                ., "Description")]]/div[contains(@class, "rightside")]')[0].text.strip()
            params['companion'] = page.xpath('//div[div[contains( \
                ., "Companion")]]/div[contains(@class, "rightside")]')[0].text.strip()
            actions = []
            table = page.xpath('//table[tr/th[contains(., "Date")]]')[0]
            for row in table.xpath('tr[td]'): # Ignore table header row.
                # import pdb; pdb.set_trace()
                action_params = {}
                cells = row.xpath('td')
                if len(cells) == 3:
                    ch = cells[1].text
                    action_params['actor'] = house[ch]
                    action_params['action'] = cells[2].text
                    action_date = cells[0].text.split()[0] # Just get date, ignore any time.
                    action_params['date'] = datetime.strptime(action_date, "%m/%d/%Y")
                    actions.append(action_params)
            bill = Bill(**params)
            bill.add_sponsor('primary', sponsors)
            for action_params in actions:
                bill.add_action(**action_params)
            return bill

    def scrape_20101SS(self, chamber, session, url):
        """Scraper for 2010 Special Sessions"""
        year_label, session_type = get_session_details(session)
        # chamber_string = get_chamber_string(url, chamber)
        bill_list_url = url%(year_label)
        with self.urlopen(bill_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_list_url)
            table = page.xpath('//table[tr/th[contains(., "Measure Status")]]')[0]
            for row in table.xpath('tr'):
                # import pdb; pdb.set_trace()
                self.scrape_20101SS_row(chamber, session, row)

    def scrape_20101SS_row(self, chamber, session, row):
        """Scrapes rows for scrape_20101SS."""
        params = {}
        params['session'] = session
        params['chamber'] = chamber
        b = row.xpath('td/a[contains(., "Status")]')
        if b: # Ignore if no match
            bill_status_url = b[0].xpath('../a[contains(., "Status")]')[0].attrib['href']
            bill_url = row.xpath('td/a[contains(@href, ".pdf")]')[0].attrib['href']
            bill = self.scrape_bill_status_page(bill_status_url, params)
            bill.add_version('Current version', bill_url)
            bill.add_source(bill_status_url)
        return

    def scrape_bill_status_page(self, url, params={}):
        """Scrapes the status page url, populating parameter dict and
        returns bill
        """
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            params['bill_id'] = page.xpath('//h3[contains(@class, "center")]/a')[0].text.split()[0]
            params['title'] = page.xpath('//div[div[contains( \
                ., "Report Title")]]/div[contains(@class, "rightside")]')[0].text.strip()
            sponsors = page.xpath('//div[div[contains( \
                ., "Introducer")]]/div[contains(@class, "rightside")]')[0].text
            subject = page.xpath('//div[div[contains( \
                ., "Measure Title")]]/div[contains(@class, "rightside")]')[0].text.strip()
            subject = subject.replace('RELATING TO ', '') # Remove lead text
            params['subject'] = subject.replace('.', '')
            params['description'] = page.xpath('//div[div[contains( \
                ., "Description")]]/div[contains(@class, "rightside")]')[0].text
            params['companion'] = page.xpath('//div[div[contains( \
                ., "Companion")]]/div[contains(@class, "rightside")]')[0].text
            if params['title'] == '':
                params['title'] = params['subject']
            actions = []
            table = page.xpath('//table[tr/th[contains(., "Date")]]')[0]
            for row in table.xpath('tr[td]'): # Ignore table header row
                # import pdb; pdb.set_trace()
                action_params = {}
                cells = row.xpath('td')
                if len(cells) == 3:
                    ch = cells[1].text
                    action_params['actor'] = house[ch]
                    action_params['action'] = cells[2].text
                    action_date = cells[0].text.split()[0] # Just get date, ignore any time.
                    try:
                        action_params['date'] = datetime.strptime(action_date, "%m/%d/%y")
                    except ValueError: # Try a YYYY format.
                        action_params['date'] = datetime.strptime(action_date, "%m/%d/%Y")
                    actions.append(action_params)
            bill = Bill(**params)
            bill.add_sponsor('primary', sponsors)
            for action_params in actions:
                bill.add_action(**action_params)
        self.save_bill(bill)
        return bill

    def scrape_20091SS(self, chamber, session, url):
        """Scraper for 2009 First Special Session"""
        year_label, session_type = get_session_details(session)
        # chamber_string = get_chamber_string(url, chamber)
        bill_list_url = url%(year_label)
        with self.urlopen(bill_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_list_url)
            table = page.xpath('//table[@id="ReportGridView"]')[0]
            for row in table.xpath('tr'):
                # import pdb; pdb.set_trace()
                self.scrape_20091SS_row(chamber, session, row)

    def scrape_20091SS_row(self, chamber, session, row):
        """Scrapes rows for scrape_20091SS."""
        params = {}
        params['session'] = session
        params['chamber'] = chamber
        b = row.xpath('td/a[contains(@id, "HyperLink1")]')
        if b: # Ignore if no match
            bill_status_url = b[0].attrib['href']
            bill_url = row.xpath('td/a[contains(@id, "HyperLinkgm1")]')[0].attrib['href']
            bill = self.scrape_2009_special_status_page(bill_status_url, params)
            bill.add_version('Current version', bill_url)
            bill.add_source(bill_status_url)
        return

    def scrape_2009_special_status_page(self, url, params={}):
        """Scrapes the status page url, populating parameter dict and
        returns bill
        """
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            params['bill_id'] = page.xpath('//a[contains(@class, "headerlink")]')[0].text
            params['title'] = page.xpath(
                '//td[contains(preceding::td[1]/b/text(), "Report Title")]')[0].text.strip()
            sponsors = page.xpath(
                '//td[contains(preceding::td[1]/b/text(), "Introducer")]')[0].text.strip()
            subject = page.xpath(
                '//td[contains(preceding::td[1]/b/text(), "Measure Title")]')[0].text.strip()
            subject = subject.replace('RELATING TO ', '') # Remove lead text
            params['subject'] = subject.replace('.', '')
            params['description'] = page.xpath(
                '//td[contains(preceding::td[1]/b/text(), "Description")]')[0].text.strip()
            params['companion'] = page.xpath(
                '//td[contains(preceding::td[1]/b/text(), "Companion")]')[0].text.strip()
            actions = []
            table = page.xpath('//table[contains(@id, "GridView1")]')[0]
            for row in table.xpath('tr[td]'): # Ignore table header row
                action_params = {}
                cells = row.xpath('td')
                if len(cells) == 3:
                    ch = cells[1].xpath('font')[0].text
                    action_params['actor'] = house[ch]
                    action_params['action'] = cells[2].xpath('font')[0].text
                    action_date = cells[0].xpath('font')[0].text.split()[0] # Just get date, ignore any time.
                    try:
                        action_params['date'] = datetime.strptime(action_date, "%m/%d/%y")
                    except ValueError: # Try a YYYY format.
                        action_params['date'] = datetime.strptime(action_date, "%m/%d/%Y")
                    actions.append(action_params)
            bill = Bill(**params)
            bill.add_sponsor('primary', sponsors)
            for action_params in actions:
                bill.add_action(**action_params)
        self.save_bill(bill)
        return bill
