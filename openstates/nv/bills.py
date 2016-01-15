import re
from datetime import datetime
from collections import defaultdict
import lxml.html
import scrapelib
from .utils import chamber_name, parse_ftp_listing
from openstates.utils import LXMLMixin
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import VoteScraper, Vote


class NVBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'nv'

    _classifiers = (
        ('Approved by the Governor', 'governor:signed'),
        ('Bill read. Veto not sustained', 'bill:veto_override:passed'),
        ('Bill read. Veto sustained', 'bill:veto_override:failed'),
        ('Enrolled and delivered to Governor', 'governor:received'),
        ('From committee: .+? adopted', 'committee:passed'),
        ('From committee: .+? pass', 'committee:passed'),
        ('Prefiled. Referred', ['bill:introduced', 'committee:referred']),
        ('Read first time. Referred', ['bill:reading:1', 'committee:referred']),
        ('Read first time.', 'bill:reading:1'),
        ('Read second time.', 'bill:reading:2'),
        ('Read third time. Lost', ['bill:failed', 'bill:reading:3']),
        ('Read third time. Passed', ['bill:passed', 'bill:reading:3']),
        ('Read third time.', 'bill:reading:3'),
        ('Rereferred', 'committee:referred'),
        ('Resolution read and adopted', 'bill:passed'),
        ('Vetoed by the Governor', 'governor:vetoed')
    )

    def scrape(self, chamber, session):
        if 'Special' in session:
            year = session[0:4]
        elif int(session) >= 71:
            year = ((int(session) - 71) * 2) + 2001
        else:
            raise NoDataForPeriod(session)

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'

        self.subject_mapping = defaultdict(list)

        if 'Special' in session:
            insert = session[-2:] + sessionsuffix + str(year) + "Special"
        else:
            insert = str(session) + sessionsuffix + str(year)
            self.scrape_subjects(insert, session, year)

        if chamber == 'upper':
            self.scrape_senate_bills(chamber, insert, session, year)
        elif chamber == 'lower':
            self.scrape_assem_bills(chamber, insert, session, year)

    def scrape_subjects(self, insert, session, year):
        url = 'http://www.leg.state.nv.us/Session/%s/Reports/TablesAndIndex/%s_%s-index.html' % (insert, year, session)

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # first, a bit about this page:
        # Level0 are the bolded titles
        # Level1,2,3,4 are detailed titles, contain links to bills
        # all links under a Level0 we can consider categorized by it
        # there are random newlines *everywhere* that should get replaced

        subject = None

        for p in doc.xpath('//p'):
            if p.get('class') == 'Level0':
                subject = p.text_content().replace('\r\n', ' ')
            else:
                if subject:
                    for a in p.xpath('.//a'):
                        bill_id = (a.text.replace('\r\n', '') if a.text
                                   else None)
                        self.subject_mapping[bill_id].append(subject)

    def scrape_senate_bills(self, chamber, insert, session, year):
        doc_type = {2: 'bill', 4: 'resolution', 7: 'concurrent resolution',
                    8: 'joint resolution'}

        for docnum, bill_type in doc_type.iteritems():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)

                page = self.get(page_path).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)

                bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                title = self.get_node(
                    root,
                    '//div[@id="content"]/table/tr[preceding-sibling::tr/td/'
                    'b[contains(text(), "By:")]]/td/em/text()')

                bill = Bill(session, chamber, bill_id, title,
                            type=bill_type)
                bill['subjects'] = list(set(self.subject_mapping[bill_id]))

                for table in root.xpath('//div[@id="content"]/table'):
                    if 'Bill Text' in table.text_content():
                        bill_text = table.xpath("string(tr/td[2]/a/@href)")
                        text_url = "http://www.leg.state.nv.us" + bill_text
                        bill.add_version("Bill Text", text_url,
                                         mimetype='application/pdf')

                primary, secondary = self.scrape_sponsors(page)

                for leg in primary:
                    bill.add_sponsor('primary', leg)
                for leg in secondary:
                    bill.add_sponsor('cosponsor', leg)

                minutes_count = 2
                for mr in root.xpath('//table[4]/tr/td[3]/a'):
                    minutes =  mr.xpath("string(@href)")
                    minutes_url = "http://www.leg.state.nv.us" + minutes
                    minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                    minutes_date = mr.xpath(minutes_date_path).split()
                    minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Agenda"
                    bill.add_document(minutes_date, minutes_url)
                    minutes_count = minutes_count + 1

                self.scrape_actions(root, bill, "upper")
                self.scrape_votes(page, page_path, bill, insert, year)
                bill.add_source(page_path)
                self.save_bill(bill)


    def scrape_assem_bills(self, chamber, insert, session, year):

        doc_type = {1: 'bill', 3: 'resolution', 5: 'concurrent resolution',
                    6: 'joint resolution',9:'petition'}
        for docnum, bill_type in doc_type.iteritems():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)
                page = self.get(page_path).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)
                root.make_links_absolute("http://www.leg.state.nv.us/")

                bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                title = self.get_node(
                    root,
                    '//div[@id="content"]/table/tr[preceding-sibling::tr/td/'
                    'b[contains(text(), "By:")]]/td/em/text()')

                bill = Bill(session, chamber, bill_id, title,
                            type=bill_type)
                bill['subjects'] = list(set(self.subject_mapping[bill_id]))
                billtext = root.xpath("//b[text()='Bill Text']")[0].getparent().getnext()
                text_urls = billtext.xpath("./a")
                for text_url in text_urls:
                    version_name = text_url.text.strip()
                    version_url = text_url.attrib['href']
                    bill.add_version(version_name, version_url,
                                 mimetype='application/pdf')

                primary, secondary = self.scrape_sponsors(page)

                for leg in primary:
                    bill.add_sponsor('primary', leg)
                for leg in secondary:
                    bill.add_sponsor('cosponsor', leg)

                minutes_count = 2
                for mr in root.xpath('//table[4]/tr/td[3]/a'):
                    minutes =  mr.xpath("string(@href)")
                    minutes_url = "http://www.leg.state.nv.us" + minutes
                    minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                    minutes_date = mr.xpath(minutes_date_path).split()
                    minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Minutes"
                    bill.add_document(minutes_date, minutes_url)
                    minutes_count = minutes_count + 1


                self.scrape_actions(root, bill, "lower")
                self.scrape_votes(page, page_path, bill, insert, year)
                bill.add_source(page_path)
                self.save_bill(bill)

    def scrape_links(self, url):
        links = []

        page = self.get(url).text
        root = lxml.html.fromstring(page)
        path = '/html/body/div[@id="ScrollMe"]/table/tr[1]/td[1]/a'
        for mr in root.xpath(path):
            if '*' not in mr.text:
                web_end = mr.xpath('string(@href)')
                links.append(web_end)
        return links


    def scrape_sponsors(self, page):
        primary = []
        sponsors = []

        doc = lxml.html.fromstring(page)
        # These bold tagged elements should contain the primary sponsors.
        b_nodes = self.get_nodes(
            doc,
            '//div[@id="content"]/table/tr/td[contains(./b/text(), "By:")]/b/'
            'text()')

        for b in b_nodes:
            name = b.strip()
            # add these as sponsors (excluding junk text)
            if name not in ('By:', 'Bolded'):
                primary.append(name)
        
        nb_nodes = self.get_nodes(
            doc,
            '//div[@id="content"]/table/tr/td[contains(./b/text(), "By:")]/text()')

        # tail of last b has remaining sponsors
        for node in nb_nodes:
            if node == ' name indicates primary sponsorship)':
                continue
            names = re.sub('([\(\r\t\n\s])', '', node).split(',')

            for name in names:
                if name:
                    sponsors.append(name.strip())

        return primary, sponsors

    def scrape_actions(self, root, bill, actor):
        path = '/html/body/div[@id="content"]/table/tr/td/p[1]'
        for mr in root.xpath(path):
            date = mr.text_content().strip()
            date = date.split()[0] + " " + date.split()[1] + " " + date.split()[2]
            date = datetime.strptime(date, "%b %d, %Y")
            for el in mr.xpath('../../following-sibling::tr[1]/td/ul/li'):
                action = el.text_content().strip()

                # skip blank actions
                if not action:
                    continue

                action = " ".join(action.split())

                # catch chamber changes
                if action.startswith('In Assembly'):
                    actor = 'lower'
                elif action.startswith('In Senate'):
                    actor = 'upper'
                elif 'Governor' in action:
                    actor = 'executive'

                action_type = 'other'
                for pattern, atype in self._classifiers:
                    if re.match(pattern, action):
                        action_type = atype
                        break


                if "Committee on" in action:
                    committees = re.findall("Committee on ([a-zA-Z, ]*)\.",action)
                    if len(committees) > 0:
                        bill.add_action(actor, action, date, type=action_type,committees=committees)
                        continue

                bill.add_action(actor, action, date, type=action_type)




    def scrape_votes(self, bill_page, page_url, bill, insert, year):
        root = lxml.html.fromstring(bill_page)
        trs = root.xpath('/html/body/div/table[6]//tr')
        assert len(trs) >= 1, "Didn't find the Final Passage Votes' table"

        for tr in trs[1:]:
            links = tr.xpath('td/a[contains(text(), "Passage")]')
            if len(links) == 0:
                self.warning("Non-passage vote found for {}; ".format(bill['bill_id']) +
                    "probably a motion for the calendar. It will be skipped.")
            else:
                assert len(links) == 1, \
                    "Too many votes found for XPath query, on bill {}".format(bill['bill_id'])
                link = links[0]

            motion = link.text
            if 'Assembly' in motion:
                chamber = 'lower'
            else:
                chamber = 'upper'

            votes = {}
            tds = tr.xpath('td')
            for td in tds:
                if td.text:
                    text = td.text.strip()
                    date = re.match('... .*?, ....',text)
                    count = re.match('(?P<category>.*?) (?P<votes>[0-9]+)[,]?',text)
                    if date:
                        vote_date = datetime.strptime(text, '%b %d, %Y')
                    elif count:
                        votes[count.group('category')] = int(count.group('votes'))

            yes = votes['Yea']
            no = votes['Nay']
            excused = votes['Excused']
            not_voting = votes['Not Voting']
            absent = votes['Absent']
            other = excused + not_voting + absent
            passed = yes > no

            vote = Vote(chamber, vote_date, motion, passed, yes, no,
                        other, not_voting=not_voting, absent=absent)

            # try to get vote details
            try:
                vote_url = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (
                    insert, link.get('href'))

                page = self.get(vote_url).text
                page = page.replace(u"\xa0", " ")
                root = lxml.html.fromstring(page)

                for el in root.xpath('//table[2]/tr'):
                    tds = el.xpath('td')
                    name = tds[1].text_content().strip()
                    vote_result = tds[2].text_content().strip()

                    if vote_result == 'Yea':
                        vote.yes(name)
                    elif vote_result == 'Nay':
                        vote.no(name)
                    else:
                        vote.other(name)
                vote.add_source(page_url)
            except scrapelib.HTTPError:
                self.warning("failed to fetch vote page, adding vote without details")

            bill.add_vote(vote)
