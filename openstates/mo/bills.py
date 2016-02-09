import re
import datetime as dt
import scrapelib

from collections import defaultdict

import lxml.html

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

from utils import (clean_text, house_get_actor_from_action,
                   senate_get_actor_from_action,find_nodes_with_matching_text)
from openstates.utils import LXMLMixin

bill_types = {
    'HB ' : 'bill',
    'HJR' : 'joint resolution',
    'HCR' : 'concurrent resolution',
    'SB ' : 'bill',
    'SJR' : 'joint resolution',
    'SCR' : 'concurrent resolution'
}


class MOBillScraper(BillScraper, LXMLMixin):

    jurisdiction = 'mo'
    _senate_base_url = 'http://www.house.mo.gov'
    # List of URLS that aren't working when we try to visit them (but
    # probably should work):
    _bad_urls = []
    _subjects = defaultdict(list)

    def __init__(self, *args, **kwargs):
        super(BillScraper, self).__init__(*args, **kwargs)
        latest_session = self.metadata['terms'][-1]['sessions'][-1]
        self._scrape_subjects(latest_session)

    def _get_action(self, actor, action):
        # Alright. This covers both chambers and everyting else.
        flags = {
            'Introduced'       : 'bill:introduced',
            'Offered'          : 'bill:introduced',
            'First Read'       : 'bill:reading:1',
            'Read Second Time' : 'bill:reading:2',
            'Second Read'      : 'bill:reading:2',
            'Third Read'       : 'bill:reading:3',
            'Referred'         : 'committee:referred',
            'Withdrawn'        : 'bill:withdrawn',
            'S adopted'        : 'bill:passed',
            'Truly Agreed To and Finally Passed' : 'bill:passed',
            'Third Read and Passed' : 'bill:passed',
            'Signed by Governor' : 'governor:signed',
            'Approved by Governor'  : 'governor:signed',
        }
        found_action = 'other'
        for flag in flags:
            if flag in action:
                found_action = flags[flag]
        return found_action

    def _get_votes(self, date, actor, action):
        ret = []
        vre = r'(?P<leader>.*)(AYES|YEAS):\s+(?P<yeas>\d+)\s+(NOES|NAYS):\s+(?P<nays>\d+).*'
        if 'YEAS' in action.upper() or 'AYES' in action.upper():
            match = re.match(vre, action)
            if match:
                v = match.groupdict()
                yes, no = int(v['yeas']), int(v['nays'])
                vote = Vote(actor, date, v['leader'],
                            (yes > no), yes, no, 0)
                ret.append(vote)
        return ret

    def _parse_cosponsors_from_bill(self, bill, url):
        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        sponsors_text = find_nodes_with_matching_text(bill_page,'//p/span',r'\s*INTRODUCED.*')
        if len(sponsors_text) == 0:
            # probably its withdrawn
            return
        sponsors_text = sponsors_text[0].text_content()
        sponsors = clean_text(sponsors_text).split(',')
        if len(sponsors) > 1: # if there are several comma separated entries, list them.
            # the sponsor and the cosponsor were already got from the previous page, so ignore those:
            sponsors = sponsors[2::]
            for part in sponsors:
                parts = re.split(r' (?i)and ',part)
                for sponsor in parts:
                    cosponsor_name = clean_text(sponsor)
                    if cosponsor_name != "":
                        cosponsor_name = cosponsor_name.replace(
                            u'\u00a0', " ") # epic hax
                        for name in re.split(r'\s+AND\s+', cosponsor_name):
                        # for name in cosponsor_name.split("AND"):
                            name = name.strip()
                            if name:
                                bill.add_sponsor('cosponsor', name)

    def _scrape_subjects(self, session):
        self._scrape_senate_subjects(session)
        self._scrape_house_subjects(session)

    def _scrape_senate_subjects(self, session):
        self.info('Collecting subject tags from upper house.')

        subject_list_url = 'http://www.senate.mo.gov/{}info/BTS_Web/'\
            'Keywords.aspx?SessionType=R'.format(session[2:4])
        subject_page = self.lxmlize(subject_list_url)

        # Create a list of all possible bill subjects.
        subjects = self.get_nodes(subject_page, '//h3')

        for subject in subjects:
            subject_text = self.get_node(
                subject,
                './a[string-length(text()) > 0]/text()[normalize-space()]')
            subject_text = re.sub(r'([\s]*\([0-9]+\)$)', '', subject_text)

            # Bills are in hidden spans after the subject labels.
            bill_ids = subject.getnext().xpath(
                './b/a/text()[normalize-space()]')

            for bill_id in bill_ids:
                self.info('Found {}.'.format(bill_id))
                self._subjects[bill_id].append(subject_text)

    def _parse_senate_billpage(self, bill_url, year):
        bill_page = self.lxmlize(bill_url)

        # get all the info needed to record the bill
        # TODO probably still needs to be fixed
        bill_id = bill_page.xpath('//*[@id="lblBillNum"]')[0].text_content()
        bill_title = bill_page.xpath('//*[@id="lblBillTitle"]')[0].text_content()
        bill_desc = bill_page.xpath('//*[@id="lblBriefDesc"]')[0].text_content()
        bill_lr = bill_page.xpath('//*[@id="lblLRNum"]')[0].text_content()

        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self._subjects:
            subs = self._subjects[bid]
            self.log("With subjects for this bill")

        self.log(bid)

        bill = Bill(year, 'upper', bill_id, bill_desc,
                    bill_lr=bill_lr, type=bill_type, subjects=subs)
        bill.add_source(bill_url)

        # Get the primary sponsor
        sponsor = bill_page.xpath('//a[@id="hlSponsor"]')[0]
        bill_sponsor = sponsor.text_content()
        bill_sponsor_link = sponsor.attrib.get('href')
        bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

        # cosponsors show up on their own page, if they exist
        cosponsor_tag = bill_page.xpath('//a[@id="hlCoSponsors"]')
        if len(cosponsor_tag) > 0 and cosponsor_tag[0].attrib.has_key('href'):
            self._parse_senate_cosponsors(bill, cosponsor_tag[0].attrib['href'])

        # get the actions
        action_url = bill_page.xpath('//a[@id="hlAllActions"]')
        if len(action_url) > 0:
            action_url =  action_url[0].attrib['href']
            #print "actions = %s" % action_url
            self._parse_senate_actions(bill, action_url)

        # stored on a separate page
        versions_url = bill_page.xpath('//a[@id="hlFullBillText"]')
        if len(versions_url) > 0 and versions_url[0].attrib.has_key('href'):
            self._parse_senate_bill_versions(bill, versions_url[0].attrib['href'])

        self.save_bill(bill)

    def _parse_senate_bill_versions(self, bill, url):
        bill.add_source(url)
        versions_page = self.get(url).text
        versions_page = lxml.html.fromstring(versions_page)
        version_tags = versions_page.xpath('//li/font/a')
        
        # some pages are updated and use different structure
        if not version_tags:
            version_tags = versions_page.xpath('//tr/td/a[contains(@href, ".pdf")]')

        for version_tag in version_tags:
            description = version_tag.text_content()
            pdf_url = version_tag.attrib['href']
            if pdf_url.endswith('pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = None
            bill.add_version(description, pdf_url, mimetype=mimetype,
                             on_duplicate='use_new')

    def _parse_senate_actions(self, bill, url):
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        bigtable = actions_page.xpath('/html/body/font/form/table/tr[3]/td/div/table/tr')

        for row in bigtable:
            date = row[0].text_content()
            date = dt.datetime.strptime(date, '%m/%d/%Y')
            action = row[1].text_content()
            actor = senate_get_actor_from_action(action)
            type_class = self._get_action(actor, action)
            bill.add_action(actor, action, date, type=type_class)

    def _parse_senate_cosponsors(self, bill, url):
        bill.add_source(url)
        cosponsors_page = self.get(url).text
        cosponsors_page = lxml.html.fromstring(cosponsors_page)
        # cosponsors are all in a table
        cosponsors = cosponsors_page.xpath('//table[@id="dgCoSponsors"]/tr/td/a')
        #print "looking for cosponsors = %s" % cosponsors

        for cosponsor_row in cosponsors:
            # cosponsors include district, so parse that out
            cosponsor_string = cosponsor_row.text_content()
            cosponsor = clean_text(cosponsor_string)
            cosponsor = cosponsor.split(',')[0]

            # they give us a link to the congressperson, so we might
            # as well keep it.
            cosponsor_url = cosponsor_row.attrib['href']

            bill.add_sponsor('cosponsor', cosponsor, sponsor_link=cosponsor_url)

    def _scrape_house_subjects(self, session):
        self.info('Collecting subject tags from lower house.')

        subject_list_url = 'http://house.mo.gov/subjectindexlist.aspx?year={}'\
            .format(session)
        subject_page = self.lxmlize(subject_list_url)

        # Create a list of all the possible bill subjects.
        subjects = self.get_nodes(
            subject_page,
            '//ul[@id="subjectindexitems"]/div/li[1]/a[1]')

        # Find the list of bills within each subject.
        for subject in subjects:
            self.info('Searching for bills in {}.'.format(subject.text))

            subject_page = self.lxmlize(subject.attrib['href'])

            bill_nodes = self.get_nodes(
                subject_page,
                '//table[@id="reportgrid"]/tbody/tr[@class="reportbillinfo"]')

            # Move onto the next subject if no bills were found.
            if bill_nodes is None or not (len(bill_nodes) > 0):
                continue

            for bill_node in bill_nodes:
                bill_id = self.get_node(
                    bill_node,
                    '(./td)[1]/a/text()[normalize-space()]')

                # Skip to the next bill if no ID could be found.
                if bill_id is None or not (len(bill_id) > 0):
                    continue

                self.info('Found {}.'.format(bill_id))
                self._subjects[bill_id].append(subject.text)

    def _parse_house_actions(self, bill, url):
        url = re.sub("BillActions", "BillActionsPrn", url)
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        rows = actions_page.xpath('//table/tr')

        for row in rows[1:]:
            # new actions are represented by having dates in the first td
            # otherwise, it's a continuation of the description from the
            # previous action
            if len(row) > 0 and row[0].tag == 'td':
                if len(row[0].text_content().strip()) > 0:
                    date = row[0].text_content().strip()
                    date = dt.datetime.strptime(date, '%m/%d/%Y')
                    action = row[2].text_content().strip()
                else:
                    action += ('\n' + row[2].text_content())
                    action = action.rstrip()
                actor = house_get_actor_from_action(action)
                type_class = self._get_action(actor, action)

                votes = self._get_votes(date, actor, action)
                for vote in votes:
                    bill.add_vote(vote)

                bill.add_action(actor, action, date, type=type_class)

    def _parse_house_billpage(self, url, year):
        url_root = re.match("(.*//.*?/)", url).group(1)

        bill_list_page = self.get(url).text
        bill_list_page = lxml.html.fromstring(bill_list_page)
        # find the first center tag, take the text after
        # 'House of Representatives' and before 'Bills' as
        # the session name
        header_tag = bill_list_page.xpath('//*[@id="ContentPlaceHolder1_lblAssemblyInfo"]')[0].text_content()
        if header_tag.find('1st Extraordinary Session') != -1:
            session = year + ' 1st Extraordinary Session'
        elif header_tag.find('2nd Extraordinary Session') != -1:
            session = year + ' 2nd Extraordinary Session'
        else:
            session = year

        bills = bill_list_page.xpath('//table[@id="billAssignGroup"]/tr')

        isEven = False
        count = 0
        for bill in bills:
            if not isEven:
                # the non even rows contain bill links, the other rows contain brief
                # descriptions of the bill.
                #print "bill = %s" % bill[0][0].attrib['href']
                count = count + 1
                #if (count > 1140):
                self._parse_house_bill(bill[0][0].attrib['href'], session)
            isEven = not isEven

    def _parse_house_bill(self, url, session):
        # using the print page makes the page simpler, and also *drastically* smaller (8k rather than 100k)
        url = re.sub("billsummary", "billsummaryprn", url)
        url = '%s/%s' % (self._senate_base_url,url)

        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        bill_page.make_links_absolute(url)

        bill_id = bill_page.xpath('//*[@class="entry-title"]')
        if len(bill_id) == 0:
            self.log("WARNING: bill summary page is blank! (%s)" % url)
            self._bad_urls.append(url)
            return
        bill_id = bill_id[0].text_content()
        bill_id = clean_text(bill_id)

        bill_desc = bill_page.xpath('//*[@class="BillDescription"]')[0].text_content()
        bill_desc = clean_text(bill_desc)

        table_rows = bill_page.xpath('//table/tr')
        # if there is a cosponsor all the rows are pushed down one for the extra row for the cosponsor:
        cosponsorOffset = 0
        if table_rows[2][0].text_content().strip() == 'Co-Sponsor:':
            cosponsorOffset = 1

        lr_label_tag = table_rows[3+cosponsorOffset]
        assert lr_label_tag[0].text_content().strip() == 'LR Number:'
        bill_lr = lr_label_tag[1].text_content()

        lastActionOffset = 0
        if table_rows[4+cosponsorOffset][0].text_content().strip() == 'Governor Action:':
            lastActionOffset = 1
        official_title_tag = table_rows[5+cosponsorOffset+lastActionOffset]
        assert official_title_tag[0].text_content().strip() == 'Bill String:'
        official_title = official_title_tag[1].text_content()

        # could substitute the description for the name,
        # but keeping it separate for now.

        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self._subjects:
            subs = self._subjects[bid]
            self.log("With subjects for this bill")

        self.log(bid)

        if bill_desc == "":
            print("ERROR: Blank title. Skipping. {} / {} / {}".format(
                bill_id, bill_desc, official_title
            ))
            # XXX: Some pages full of blank bills.
            return

        bill = Bill(session, 'lower', bill_id, bill_desc, bill_url=url,
                    bill_lr=bill_lr, official_title=official_title,
                    type=bill_type, subjects=subs)
        bill.add_source(url)

        bill_sponsor = clean_text(table_rows[0][1].text_content())
        try:
            bill_sponsor_link = table_rows[0][1][0].attrib['href']
        except IndexError:
            return

        if bill_sponsor_link:
            bill_sponsor_link = '%s%s' % (self._senate_base_url,bill_sponsor_link)

        bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

        # check for cosponsors
        if cosponsorOffset == 1:
            if len(table_rows[2][1]) == 1: # just a name
                cosponsor = table_rows[2][1][0]
                bill.add_sponsor('cosponsor', cosponsor.text_content(),
                                 sponsor_link='%s/%s' % (
                                     self._senate_base_url,
                                     cosponsor.attrib['href']
                                ))
            else: # name ... etal
                try:
                    cosponsor = table_rows[2][1][0]
                    bill.add_sponsor('cosponsor',
                                     clean_text(cosponsor.text_content()),
                                     sponsor_link='%s/%s' % (
                                         self._senate_base_url,
                                         cosponsor.attrib['href']
                                     ))
                    sponsors_url, = bill_page.xpath(
                        "//a[contains(@href, 'CoSponsors.aspx')]/@href")
                    self._parse_cosponsors_from_bill(bill, sponsors_url)
                except scrapelib.HTTPError as e:
                    self.log("WARNING: " + str(e))
                    self._bad_urls.append(url)
                    self.log( "WARNING: no bill summary page (%s)" % url )

        # actions_link_tag = bill_page.xpath('//div[@class="Sections"]/a')[0]
        # actions_link = '%s/%s' % (self._senate_base_url,actions_link_tag.attrib['href'])
        # actions_link = re.sub("content", "print", actions_link)

        actions_link, = bill_page.xpath(
            "//a[contains(@href, 'BillActions.aspx')]/@href")
        self._parse_house_actions(bill, actions_link)

        # get bill versions
        doc_tags = bill_page.xpath('//div[@class="BillDocsSection"][1]/span')
        for doc_tag in reversed(doc_tags):
            doc = clean_text(doc_tag.text_content())
            text_url = '%s%s' % (
                self._senate_base_url,
                doc_tag[0].attrib['href']
            )
            bill.add_document(doc, text_url,
                              mimetype="text/html")

        # get bill versions
        version_tags = bill_page.xpath('//div[@class="BillDocsSection"][2]/span')
        for version_tag in reversed(version_tags):
            version = clean_text(version_tag.text_content())
            for vurl in version_tag.xpath(".//a"):
                if vurl.text == 'PDF':
                    mimetype = 'application/pdf'
                else:
                    mimetype = 'text/html'
                bill.add_version(version, vurl.attrib['href'],
                                 on_duplicate='use_new', mimetype=mimetype)
        self.save_bill(bill)

    def _scrape_upper_chamber(self, year):
        # We only have data back to 2005.
        if int(year) < 2005:
            raise NoDataForPeriod(year)

        self.info('Scraping bills from upper chamber.')

        year2 = "%02d" % (int(year) % 100)

        # Save the root URL, since we'll use it later.
        bill_root = 'http://www.senate.mo.gov/{}info/BTS_Web/'.format(year2)
        index_url = bill_root + 'BillList.aspx?SessionType=R'

        index_page = self.get(index_url).text
        index_page = lxml.html.fromstring(index_page)
        # Each bill is in it's own table (nested within a larger table).
        bill_tables = index_page.xpath('//a[@id]')

        if not bill_tables:
            return

        for bill_table in bill_tables:
            # Here we just search the whole table string to get the BillID that
            # the MO senate site uses.
            if re.search(r'dgBillList.*hlBillNum',bill_table.attrib['id']):
                #print "keys = %s" % bill_table.attrib['id']
                #print "table = %s " % bill_table.attrib.get('href')
                self._parse_senate_billpage(bill_root + bill_table.attrib.get('href'), year)
                #print "one down!"

    def _scrape_lower_chamber(self, year):
        # We only have data back to 2000.
        if int(year) < 2000:
            raise NoDataForPeriod(year)

        self.info('Scraping bills from lower chamber.')

        bill_page_url = '{}/BillList.aspx?year={}'.format(
            self._senate_base_url,year)
        self._parse_house_billpage(bill_page_url, year)

    def scrape(self, chamber, year):
        getattr(self, '_scrape_' + chamber + '_chamber')(year)

        if len(self._bad_urls) > 0:
            self.warn('WARNINGS:')
            for url in self._bad_urls:
                self.warn('{}'.format(url))
