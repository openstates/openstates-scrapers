from __future__ import unicode_literals
import re
import time
import itertools
import requests
from datetime import datetime

import lxml.html

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

from .actions import Categorizer


class MABillScraper(BillScraper):
    jurisdiction = 'ma'
    categorizer = Categorizer()
    session_filters = {}
    chamber_filters = {}

    chamber_map = {'lower':'House', 'upper':'Senate'}
    chamber_map_reverse = {'House':'lower', 'Senate':'upper', 'Executive':'executive', 'Joint':'joint'}

    def __init__(self, *args, **kwargs):
        super(MABillScraper, self).__init__(*args, **kwargs)
        # forcing these values so that 500s come back as skipped bills
        # self.retry_attempts = 0
        self.raise_errors = False

    def format_bill_number(self, raw):
        return raw.replace('Bill ','').replace('.',' ').strip()

    def get_refiners(self, page, refinerName):
        # Get the possible values for each category of refiners,
        # e.g. House, Senate for lawsbranchname (Branch)
        filters = page.xpath("//div[@data-refinername='{}']/div/label".format(refinerName))

        refiner_list = {}
        for refiner_filter in filters:
            label = re.sub(r'\([^)]*\)', "", refiner_filter.xpath('text()')[1]).strip()
            refiner = refiner_filter.xpath('input/@data-refinertoken')[0].replace('"','')
            refiner_list[label] = refiner
        return refiner_list

    def scrape(self, chamber, session):
        # for the chamber of the action
        #chamber_map = {'House': 'lower', 'Senate': 'upper', 'Joint': 'joint','Governor': 'executive'}
        #self.scrape_bill(session,'S11',chamber)

        # Pull the search page to get the filters
        search_url = 'https://malegislature.gov/Bills/Search'
        page = lxml.html.fromstring(self.get(search_url).text)

        self.session_filters = self.get_refiners(page, 'lawsgeneralcourt')
        self.chamber_filters = self.get_refiners(page, 'lawsbranchname')
        #doctype_filters = self.get_refiners(page, 'lawsfilingtype')
# remove nick lines before final
        lastPage = self.get_max_pages(session, chamber)
        lastPage = 1 # nick
        for pageNumber in range(1, lastPage + 1):
            bills = self.list_bills(session, chamber, pageNumber)
            bill_count = 0 # nick
            for bill in bills:
                # if bill > 4: didn't work
                bill = self.format_bill_number(bill).replace(' ','')
                if bill != 'H58':
                    continue
                self.scrape_bill(session, bill, chamber )
                break # remove after testing

    def list_bills(self, session, chamber, pageNumber):
        session_filter = self.session_filters[session]
        chamber_filter = self.chamber_filters[self.chamber_map[chamber]]
        search_url = u'https://malegislature.gov/Bills/Search?SearchTerms=&Page={}&Refinements%5Blawsgeneralcourt%5D={}&&Refinements%5Blawsbranchname%5D={}'.format(
            pageNumber, session_filter, chamber_filter)

        page = lxml.html.fromstring(requests.get(search_url).text)
        resultRows = page.xpath('//table[@id="searchTable"]/tbody/tr/td[2]/a/text()')
        return resultRows

    def get_max_pages(self, session, chamber):
        session_filter = self.session_filters[session]
        try:
            chamber_filter = self.chamber_filters[self.chamber_map[chamber]]
        except KeyError:
            self.warning("No bills found for %s" % chamber)
            return 0

        search_url = u'https://malegislature.gov/Bills/Search?SearchTerms=&Page=1&Refinements%5Blawsgeneralcourt%5D={}&&Refinements%5Blawsbranchname%5D={}'.format(
            session_filter, chamber_filter)

        page = lxml.html.fromstring(requests.get(search_url).text)

        if page.xpath('//ul[contains(@class,"pagination-sm")]/li[last()]/a/@onclick'):
            maxPage = page.xpath('//ul[contains(@class,"pagination-sm")]/li[last()]/a/@onclick')[0]
            maxPage = re.sub(r'[^\d]', '', maxPage).strip()
        else:
            maxPage = 1

        return int(maxPage)

    def scrape_bill(self, session, bill_id, chamber):
        #https://malegislature.gov/Bills/189/SD2739
        session_for_url =  self.replace_non_digits(session)
        bill_url = u'https://malegislature.gov/Bills/{}/{}'.format(session_for_url, bill_id)

        try:
            response = requests.get(bill_url)
        except requests.exceptions.RequestException as e:
            self.warning(u'Server Error on {}'.format(bill_url))
            return False

        html = response.text

        page = lxml.html.fromstring(html)

        if page.xpath('//div[contains(@class, "followable")]/h1/text()'):
            bill_number = page.xpath('//div[contains(@class, "followable")]/h1/text()')[0]
        else:
            self.warning(u'Server Error on {}'.format(bill_url))
            return False

        bill_title = page.xpath('//div[@id="contentContainer"]/div/div/h2/text()')[0]

        bill_summary = ''
        if page.xpath('//p[@id="pinslip"]/text()'):
            bill_summary = page.xpath('//p[@id="pinslip"]/text()')[0]

        bill_id = re.sub(r'[^S|H|D|\d]','',bill_id)

        bill = Bill(session, chamber,bill_id, bill_title,
                    summary=bill_summary)
        bill.add_source(bill_url)


        #https://malegislature.gov/Bills/189/SD2739 has a presenter
        #https://malegislature.gov/Bills/189/S2168 no sponsor
        # Find the non-blank text of the dt following Sponsor or Presenter,
        # including any child link text.
        sponsor = page.xpath('//dt[text()="Sponsor:" or text()="Presenter:"]/following-sibling::dd/descendant-or-self::*/text()[normalize-space()]')
        if sponsor:
            sponsor = sponsor[0].strip()
            bill.add_sponsor('primary', sponsor)

        self.scrape_cosponsors(bill, bill_url)


        version = page.xpath("//div[contains(@class, 'modalBtnGroup')]/a[contains(text(), 'Download PDF') and not(@disabled)]/@href")
        if version:
            version_url = "https://malegislature.gov{}".format(version[0])
            bill.add_version('Bill Text', version_url,
                    mimetype='application/pdf')

        self.scrape_actions(bill, bill_url)

        self.save_bill(bill)

    def scrape_cosponsors(self, bill, bill_url):
        #https://malegislature.gov/Bills/189/S1194/CoSponsor
        cosponsor_url = "{}/CoSponsor".format(bill_url)
        html = self.get_as_ajax(cosponsor_url).text
        page = lxml.html.fromstring(html)
        cosponsor_rows = page.xpath('//tbody/tr')
        for row in cosponsor_rows:
            # careful, not everyone is a linked representative
            # https://malegislature.gov/Bills/189/S740/CoSponsor
            cosponsor_name = row.xpath('string(td[1])')
            cosponsor_district = ''
            if row.xpath('td[2]/text()'):
                cosponsor_district = row.xpath('td[2]/text()')[0]

            #Filter the sponsor out of the petitioners list
            if not any(sponsor['name'] == cosponsor_name for sponsor in bill['sponsors']):
                bill.add_sponsor('cosponsor', cosponsor_name, district=cosponsor_district)

    def scrape_actions(self, bill, bill_url):
        # scrape_action_page adds the actions, and also returns the Page xpath object
        # so that we can check for a paginator
        page = self.scrape_action_page(bill, bill_url, 1)

        max_page = page.xpath('//ul[contains(@class,"pagination-sm")]/li[last()]/a/@onclick')
        if max_page:
            max_page = re.sub(r'[^\d]', '', max_page[0]).strip()
            for counter in range(2, int(max_page)+1):
                page = self.scrape_action_page(bill, bill_url, counter)
                #https://malegislature.gov/Bills/189/S3/BillHistory?pageNumber=2


    def scrape_action_page(self, bill, bill_url, page_number):
        actions_url = "{}/BillHistory?pageNumber={}".format(bill_url, page_number)
        page = lxml.html.fromstring(self.get_as_ajax(actions_url).text)
        action_rows = page.xpath('//tbody/tr')
        for row in action_rows:
            action_date = row.xpath('td[1]/text()')[0]
            action_date = datetime.strptime(action_date, '%m/%d/%Y')

            if row.xpath('td[2]/text()'):
                action_actor = row.xpath('td[2]/text()')[0]
                action_actor = self.chamber_map_reverse[action_actor.strip()]

            action_name = row.xpath('string(td[3])')
            attrs = self.categorizer.categorize(action_name)
            # House votes
            if "Supplement" in action_name:
                actor = "lower"
                vote_action = action_name.split(' -')[0]
                y = int(action_name.strip().split('-')[1].split('YEAS')[0])
                n = int(action_name.strip().split('YEAS to')[1].split('NAYS')[0])
                o = 0 # placeholder
                cached_vote = Vote(actor, action_date, vote_action, y > n, y, n, o)
                bill.add_vote(cached_vote)

            # Senate votes
            if "Roll Call" in action_name:
                actor = "upper"
                 #placeholder
                vote_action = action_name.split(' -')[0]
                y = int(action_name.strip().split('Yeas')[1].split('-')[0])

                n = int(action_name.strip().split('Nays')[1].split(')')[0])
                o = 0 # placeholder
                cached_vote = Vote(actor, action_date, vote_action, y > n, y, n, o)
                bill.add_vote(cached_vote)
                bill.add_document(row.xpath('string(td[3]/a/text())'),
                    'malegislature.gov' + row.xpath('string(td[3]/a/@href)'),
                    mimetype='application/pdf')


# rewrite to add source
                #cached_vote.add_source('malegislature.gov/' + row)
# Not parsing 'paired' for now, include other votes (not yes no)
                #create vote object from pdf


            #TODO: categorize action
            bill.add_action(action_actor, action_name, action_date, **attrs)
        return page

    def get_as_ajax(self, url):
        #set the X-Requested-With:XMLHttpRequest so the server only sends along the bits we want
        s = requests.Session()
        s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
        return s.get(url)

    def replace_non_digits(self, str):
        return re.sub(r'[^\d]', '', str).strip()
