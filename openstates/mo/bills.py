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

bill_types = {
    "HB " : "bill",
    "HJR" : "joint resolution",
    "HCR" : "concurrent resolution",
    "SB " : "bill",
    "SJR" : "joint resolution",
    "SCR" : "concurrent resolution"
}

class MOBillScraper(BillScraper):

    jurisdiction = 'mo'
    senate_base_url = 'http://www.house.mo.gov'
    # a list of URLS that aren't working when we try to visit them (but probably should work):
    bad_urls = []
    subjects = defaultdict(list)

    def __init__(self, *args, **kwargs):
        super(BillScraper, self).__init__(*args, **kwargs)
        lk_session = self.metadata['terms'][0]['sessions'][-1]
        self.scrape_subjects(lk_session)

    def url_xpath(self, url, path):
        doc = lxml.html.fromstring(self.get(url).text)
        return doc.xpath(path)

    def scrape_subjects(self, session):
        self.scrape_house_subjects(session)
        self.scrape_senate_subjects(session)

    def scrape_senate_subjects(self, session):
        short = session[2:4]
        subject_url = "http://www.senate.mo.gov/%sinfo/BTS_Web/Keywords.aspx?SessionType=R" % (
            short
        )
        subject_page = self.get(subject_url).text
        subject_page = lxml.html.fromstring(subject_page)
        subjects = subject_page.xpath("//h3")
        for subject in subjects:
            subject_text = subject.text_content()
            if ")" in subject_text:
                subject_text = subject_text[:subject_text.find("(")].strip()

            bills = subject.getnext().xpath("./b/a")
            for bill in bills:
                bill_id = bill.text.replace(" ", "")
                self.subjects[bill_id].append(subject_text)

    def scrape_house_subjects(self, session):
        subject_url = "http://house.mo.gov/subjectindexlist.aspx"
        subject_page = self.get(subject_url).text
        subject_page = lxml.html.fromstring(subject_page)
        # OK. Let's load all the subjects up.
        subjects = subject_page.xpath("//ul[@id='subjectindexitems']/div/li")
        for subject in subjects:
            ahref = subject.xpath("./a")[0]
            if ahref.text_content().strip() == "":
                continue
            link = ahref.attrib['href']
            link = self.senate_base_url + "/" + link
            rows = self.url_xpath(link, "//table[@id='reportgrid']/tbody/tr")
            for row in rows:
                bill_id = row.xpath("./td")[0].xpath("./a")
                if len(bill_id) == 0:
                    continue
                bill_id = bill_id[0].text
                self.subjects[bill_id].append(subject.text_content())

    def scrape(self, chamber, year):
        # wrapper to call senate or house scraper. No year check
        # here, since house and senate have different backdates
        if chamber == 'upper':
            self.scrape_senate(year)
        elif chamber == 'lower':
            self.scrape_house(year)
        if len(self.bad_urls) > 0:
            self.log("WARNINGS:")
            for url in self.bad_urls:
                self.log( "%s" % url )

    def scrape_senate(self, year):
        # We only have data from 2005-present
        if int(year) < 2005 or int(year) > dt.date.today().year:
            raise NoDataForPeriod(year)

        year2 = "%02d" % (int(year) % 100)

        # year is mixed in to the directory. set a root_url, since
        # we'll use it later
        bill_root = 'http://www.senate.mo.gov/%sinfo/BTS_Web/' % year2
        index_url = bill_root + 'BillList.aspx?SessionType=R'
        #print "index = %s" % index_url

        index_page = self.get(index_url).text
        index_page = lxml.html.fromstring(index_page)
        # each bill is in it's own table (nested in a larger table)
        bill_tables = index_page.xpath('//a[@id]')

        if not bill_tables:
            return

        for bill_table in bill_tables:
            # here we just search the whole table string to get
            # the BillID that the MO senate site uses
            if re.search(r'dgBillList.*hlBillNum',bill_table.attrib['id']):
                #print "keys = %s" % bill_table.attrib['id']
                #print "table = %s " % bill_table.attrib.get('href')
                self.parse_senate_billpage(bill_root + bill_table.attrib.get('href'), year)
                #print "one down!"

    def parse_senate_billpage(self, bill_url, year):
        bill_page = self.get(bill_url).text
        bill_page = lxml.html.fromstring(bill_page)
        # get all the info needed to record the bill
        # TODO probably still needs to be fixed
        bill_id = bill_page.xpath('//*[@id="lblBillNum"]')[0].text_content()
        bill_title = bill_page.xpath('//*[@id="lblBillTitle"]')[0].text_content()
        bill_desc = bill_page.xpath('//*[@id="lblBriefDesc"]')[0].text_content()
        bill_lr = bill_page.xpath('//*[@id="lblLRNum"]')[0].text_content()
        #print "bill id = "+ bill_id

        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self.subjects:
            subs = self.subjects[bid]
            self.log("With subjects for this bill")

        self.log(bid)

        bill = Bill(year, 'upper', bill_id, bill_desc,
                    bill_lr=bill_lr, type=bill_type, subjects=subs)
        bill.add_source(bill_url)

        # Get the primary sponsor
        sponsor = bill_page.xpath('//*[@id="hlSponsor"]')[0]
        bill_sponsor = sponsor.text_content()
        bill_sponsor_link = sponsor.attrib.get('href')
        bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

        # cosponsors show up on their own page, if they exist
        cosponsor_tag = bill_page.xpath('//*[@id="hlCoSponsors"]')
        if len(cosponsor_tag) > 0 and cosponsor_tag[0].attrib.has_key('href'):
            self.parse_senate_cosponsors(bill, cosponsor_tag[0].attrib['href'])

        # get the actions
        action_url = bill_page.xpath('//*[@id="hlAllActions"]')
        if len(action_url) > 0:
            action_url =  action_url[0].attrib['href']
            #print "actions = %s" % action_url
            self.parse_senate_actions(bill, action_url)

        # stored on a separate page
        versions_url = bill_page.xpath('//*[@id="hlFullBillText"]')

        if len(versions_url) > 0 and versions_url[0].attrib.has_key('href'):
            self.parse_senate_bill_versions(bill, versions_url[0].attrib['href'])

        self.save_bill(bill)

    def parse_senate_bill_versions(self, bill, url):
        bill.add_source(url)
        versions_page = self.get(url).text
        versions_page = lxml.html.fromstring(versions_page)
        version_tags = versions_page.xpath('//li/font/a')

        # fixes for new session b/c of change in page structure
        if len(version_tags) == 0:
            version_tags = versions_page.xpath('//tr/td/a[not(@id="hlReturnBill")]')

        for version_tag in version_tags:
            description = version_tag.text_content()
            
            pdf_url = version_tag.attrib['href']
            if pdf_url.endswith('pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = None
            
            bill.add_version(description, pdf_url, mimetype=mimetype,
                             on_duplicate='use_new')

    def get_action(self, actor, action):
        # Alright. This covers both chambers and everyting else.
        flags = {
            "Introduced"       : "bill:introduced",
            "Offered"          : "bill:introduced",
            "First Read"       : "bill:reading:1",
            "Read Second Time" : "bill:reading:2",
            "Second Read"      : "bill:reading:2",
            "Third Read"       : "bill:reading:3",
            "Referred"         : "committee:referred",
            "Withdrawn"        : "bill:withdrawn",
            "S adopted"        : "bill:passed",

            "Truly Agreed To and Finally Passed": "bill:passed",
            "Third Read and Passed": "bill:passed",

            "Approved by Governor" : "governor:signed",
        }
        ret = []
        for flag in flags:
            if flag in action:
                ret.append(flags[flag])
        if len(ret) == 0:
            ret.append("other")
        return ret

    def get_votes(self, date, actor, action):
        ret = []
        vre = r"(?P<leader>.*)(AYES|YEAS):\s+(?P<yeas>\d+)\s+(NOES|NAYS):\s+(?P<nays>\d+).*"
        if "YEAS" in action.upper() or "AYES" in action.upper():
            match = re.match(vre, action)
            if match:
                v = match.groupdict()
                yes, no = int(v['yeas']), int(v['nays'])
                vote = Vote(actor, date, v['leader'],
                            (yes > no), yes, no, 0)
                ret.append(vote)
        return ret


    def parse_senate_actions(self, bill, url):
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        bigtable = actions_page.xpath('/html/body/font/form/table/tr[3]/td/div/table/tr')

        for row in bigtable:
            date = row[0].text_content()
            date = dt.datetime.strptime(date, '%m/%d/%Y')
            action = row[1].text_content()
            actor = senate_get_actor_from_action(action)
            type_class = self.get_action(actor, action)
            bill.add_action(actor, action, date, type=type_class)

    def parse_senate_cosponsors(self, bill, url):
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

    def scrape_house(self, year):
        if int(year) < 2000 or int(year) > dt.date.today().year:
            raise NoDataForPeriod(year)

        bill_page_url = ('%s/BillList.aspx?year=%s' % (self.senate_base_url,year))
        self.parse_house_billpage(bill_page_url, year)

    def parse_house_billpage(self, url, year):
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
                self.parse_house_bill(bill[0][0].attrib['href'], session)
            isEven = not isEven


    def parse_house_bill(self, url, session):
        # using the print page makes the page simpler, and also *drastically* smaller (8k rather than 100k)
        url = re.sub("billsummary", "billsummaryprn", url)
        url = '%s/%s' % (self.senate_base_url,url)

        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        bill_page.make_links_absolute(url)

        bill_id = bill_page.xpath('//*[@class="entry-title"]')
        if len(bill_id) == 0:
            self.log("WARNING: bill summary page is blank! (%s)" % url)
            self.bad_urls.append(url)
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

        if bid in self.subjects:
            subs = self.subjects[bid]
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
            bill_sponsor_link = '%s%s' % (self.senate_base_url,bill_sponsor_link)

        bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

        # check for cosponsors
        if cosponsorOffset == 1:
            if len(table_rows[2][1]) == 1: # just a name
                cosponsor = table_rows[2][1][0]
                bill.add_sponsor('cosponsor', cosponsor.text_content(),
                                 sponsor_link='%s/%s' % (
                                     self.senate_base_url,
                                     cosponsor.attrib['href']
                                ))
            else: # name ... etal
                try:
                    cosponsor = table_rows[2][1][0]
                    bill.add_sponsor('cosponsor',
                                     clean_text(cosponsor.text_content()),
                                     sponsor_link='%s/%s' % (
                                         self.senate_base_url,
                                         cosponsor.attrib['href']
                                     ))
                    sponsors_url, = bill_page.xpath(
                        "//a[contains(@href, 'CoSponsors.aspx')]/@href")
                    self.parse_cosponsors_from_bill(bill, sponsors_url)
                except scrapelib.HTTPError as e:
                    self.log("WARNING: " + str(e))
                    self.bad_urls.append(url)
                    self.log( "WARNING: no bill summary page (%s)" % url )

        # actions_link_tag = bill_page.xpath('//div[@class="Sections"]/a')[0]
        # actions_link = '%s/%s' % (self.senate_base_url,actions_link_tag.attrib['href'])
        # actions_link = re.sub("content", "print", actions_link)

        actions_link, = bill_page.xpath(
            "//a[contains(@href, 'BillActions.aspx')]/@href")
        self.parse_house_actions(bill, actions_link)

        # get bill versions
        doc_tags = bill_page.xpath('//div[@class="BillDocsSection"][1]/span')
        for doc_tag in reversed(doc_tags):
            doc = clean_text(doc_tag.text_content())
            text_url = '%s%s' % (
                self.senate_base_url,
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

    def parse_cosponsors_from_bill(self, bill, url):
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

    def parse_house_actions(self, bill, url):
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
                type_class = self.get_action(actor, action)

                votes = self.get_votes(date, actor, action)
                for vote in votes:
                    bill.add_vote(vote)

                bill.add_action(actor, action, date, type=type_class)
