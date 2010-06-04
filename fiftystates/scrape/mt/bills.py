import os
import re
from datetime import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.mt import metadata

import html5lib
import lxml.html
from lxml.etree import ElementTree

actor_map = {
    '(S)': 'upper',
    '(H)': 'lower',
    '(C)': 'clerk',
    }

sponsor_map = {
    'Primary Sponsor': 'primary'
    }

vote_passage_indicators = ['Adopted',
                           'Appointed',
                           'Carried',
                           'Concurred',
                           'Dissolved',
                           'Passed',
                           'Rereferred to Committee',
                           'Transmitted to',
                           'Veto Overidden',
                           'Veto Overridden']
vote_failure_indicators = ['Failed',
                           'Rejected',
                           ]
vote_ambiguous_indicators = [
    'Indefinitely Postponed',
    'On Motion Rules Suspended',
    'Pass Consideration',
    'Reconsidered Previous',
    'Rules Suspended',
    'Segregated from Committee',
    'Special Action',
    'Sponsor List Modified',
    'Tabled',
    'Taken from']

class MTBillScraper(BillScraper):
    #must set state attribute as the state's abbreviated name
    state = 'mt'

    def __init__(self, *args, **kwargs):
        super(MTBillScraper, self).__init__(*args, **kwargs)
        self.parser = html5lib.HTMLParser(tree = html5lib.treebuilders.getTreeBuilder('lxml')).parse

        self.search_url_template = "http://laws.leg.mt.gov/laws%s/LAW0203W$BSRV.ActionQuery?P_BLTP_BILL_TYP_CD=%s&P_BILL_NO=%s&P_BILL_DFT_NO=&Z_ACTION=Find&P_SBJ_DESCR=&P_SBJT_SBJ_CD=&P_LST_NM1=&P_ENTY_ID_SEQ="

    def getSession(self, year):
        for session, years in metadata['session_details'].items():
            if year in years['years']:
                return session

    def scrape(self, chamber, year):
        year = int(year)
        session = self.getSession(year)
        #2 year terms starting on odd year, so if even number, use the previous odd year
        if year < 1999:
            raise NoDataForYear(year)
        if year % 2 == 0:
            year -= 1

        if year == 1999:
            base_bill_url = 'http://data.opi.mt.gov/bills/BillHtml/'
        else:
            base_bill_url = 'http://data.opi.mt.gov/bills/%d/BillHtml/' % year
        index_page = ElementTree(lxml.html.fromstring(self.urlopen(base_bill_url)))

        bill_urls = []
        for bill_anchor in index_page.findall('//a'):
            # See 2009 HB 645
            if bill_anchor.text.find("govlineveto") == -1:
                # House bills start with H, Senate bills start with S
                if chamber == 'lower' and bill_anchor.text.startswith('H'):
                    bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))
                elif chamber == 'upper' and bill_anchor.text.startswith('S'):
                    bill_urls.append("%s%s" % (base_bill_url, bill_anchor.text))

        for bill_url in bill_urls:
            bill = self.parse_bill(bill_url, session, chamber)
            self.save_bill(bill)

    def parse_bill(self, bill_url, session, chamber):
        bill = None
        bill_page = ElementTree(lxml.html.fromstring(self.urlopen(bill_url)))
        for anchor in bill_page.findall('//a'):
            if (anchor.text_content().startswith('status of') or
                anchor.text_content().startswith('Detailed Information (status)')):
                status_url = anchor.attrib['href'].replace("\r", "").replace("\n", "")
                bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)
            elif anchor.text_content().startswith('This bill in WP'):
                index_url = anchor.attrib['href']
                index_url = index_url[0:index_url.rindex('/')]
                # this looks weird.  See http://data.opi.mt.gov/bills/BillHtml/SB0002.htm for why
                index_url = index_url[index_url.rindex("http://"):]
                self.add_bill_versions(bill, index_url)

        if bill is None:
            # No bill was found.  Maybe something like HB0790 in the 2005 session?
            # We can search for the bill metadata.
            page_name = bill_url.split("/")[-1].split(".")[0]
            bill_type = page_name[0:2]
            bill_number = page_name[2:]
            laws_year = metadata['session_details'][session]['years'][0] % 100

            status_url = self.search_url_template % (laws_year, bill_type, bill_number)
            bill = self.parse_bill_status_page(status_url, bill_url, session, chamber)
        return bill

    def parse_bill_status_page(self, status_url, bill_url, session, chamber):
        status_page = ElementTree(lxml.html.fromstring(self.urlopen(status_url)))
        # see 2007 HB 2... weird.
        try:
            bill_id = status_page.xpath("/div/form[1]/table[2]/tr[2]/td[2]")[0].text_content()
        except IndexError:
            bill_id = status_page.xpath('/html/html[2]/tr[1]/td[2]')[0].text_content()

        try:
            title = status_page.xpath("/div/form[1]/table[2]/tr[3]/td[2]")[0].text_content()
        except IndexError:
            title = status_page.xpath('/html/html[3]/tr[1]/td[2]')[0].text_content()

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(bill_url)

        self.add_sponsors(bill, status_page)
        self.add_actions(bill, status_page)

        return bill


    def add_actions(self, bill, status_page):
        for action in status_page.xpath('/div/form[3]/table[1]/tr')[1:]:
            try:
                actor = actor_map[action.xpath("td[1]")[0].text_content().split(" ")[0]]
                action_name = action.xpath("td[1]")[0].text_content().replace(actor, "")[4:].strip()
            except KeyError:
                actor = ''
                action_name = action.xpath("td[1]")[0].text_content().strip()

            action_date = datetime.strptime(action.xpath("td[2]")[0].text, '%m/%d/%Y')
            action_votes_yes = action.xpath("td[3]")[0].text_content().replace("&nbsp", "")
            action_votes_no = action.xpath("td[4]")[0].text_content().replace("&nbsp", "")
            action_committee = action.xpath("td[5]")[0].text.replace("&nbsp", "")

            bill.add_action(actor, action_name, action_date)

            # TODO: Review... should something be both an action and a vote?
            try:
                action_votes_yes = int(action_votes_yes)
                action_votes_no = int(action_votes_no)
                passed = None
                # some actions take a super majority, so we aren't just comparing the yeas and nays here.
                for i in vote_passage_indicators:
                    if action_name.count(i):
                        passed = True
                for i in vote_failure_indicators:
                    if action_name.count(i) and passed == True:
                        # a quick explanation:  originally an exception was
                        # thrown if both passage and failure indicators were
                        # present because I thought that would be a bug in my
                        # lists.  Then I found 2007 HB 160.
                        # Now passed = False if the nays outnumber the yays..
                        # I won't automatically mark it as passed if the yays
                        # ounumber the nays because I don't know what requires
                        # a supermajority in MT.
                        if action_votes_no >= action_votes_yes:
                            passed = False
                        else:
                            raise Exception ("passage and failure indicator both present: %s" % action_name)
                    if action_name.count(i) and passed == None:
                        passed = False
                for i in vote_ambiguous_indicators:
                    if action_name.count(i):
                        passed = action_votes_yes > action_votes_no
                if passed is None:
                    raise Exception("Unknown passage: %s" % action_name)
                bill.add_vote(Vote(bill['chamber'],
                                   action_date,
                                   action_name,
                                   passed,
                                   action_votes_yes,
                                   action_votes_no,
                                   0))
            except ValueError:
                pass


    def add_sponsors(self, bill, status_page):
        for sponsor_row in status_page.xpath('/div/form[6]/table[1]/tr')[1:]:
            sponsor_type = sponsor_row.xpath("td[1]")[0].text
            sponsor_last_name = sponsor_row.xpath("td[2]")[0].text
            sponsor_first_name = sponsor_row.xpath("td[3]")[0].text
            sponsor_middle_initial = sponsor_row.xpath("td[4]")[0].text

            sponsor_middle_initial = sponsor_middle_initial.replace("&nbsp", "")
            sponsor_full_name = "%s, %s %s" % (sponsor_last_name,  sponsor_first_name, sponsor_middle_initial)
            sponsor_full_name = sponsor_full_name.strip()

            if sponsor_map.has_key(sponsor_type):
                sponsor_type = sponsor_map[sponsor_type]
            bill.add_sponsor(sponsor_type, sponsor_full_name)

    def add_bill_versions(self, bill, index_url):
        # This method won't pick up bill versions where the bill is published
        # exclusively in PDF.  See 2009 HB 645 for a sample
        index_page = ElementTree(lxml.html.fromstring(self.urlopen(index_url)))
        tokens = bill['bill_id'].split(" ")
        bill_regex = re.compile("%s0*%s\_" % (tokens[0], tokens[1]))
        for anchor in index_page.findall('//a'):
            if bill_regex.match(anchor.text_content()) is not None:
                file_name = anchor.text_content()
                version = file_name[file_name.find('_')+1:file_name.find('.')]
                version_title = 'Final Version'
                if version != 'x':
                    version_title = 'Version %s' % version

                version_url = index_url[0:index_url.find('bills')-1] + anchor.attrib['href']
                bill.add_version(version_title, version_url)
