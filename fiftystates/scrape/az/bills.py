import datetime, re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.az import utils

from lxml import etree, html

base_url = 'http://www.azleg.gov/'

class AZBillScraper(BillScraper):
    state = 'az'
    def get_session_id(self, session):
        """
        returns the session id for a given session
        """
        return self.metadata['session_details'][session]['session_id']
        
    def get_bill_type(self, bill_id):
        """
        Returns the bill type from its abbreviation
        """
        bill_types = {
                      'SB': 'bill',
                      'SM': 'memorial',
                      'SR': 'resolution',
                      'SCR': 'concurrent resolution',
                      'SCM': 'concurrent memorial',
                      'SJR': 'joint resolution',
                      'HB': 'bill',
                      'HM': 'memorial',
                      'HR': 'resolution',
                      'HCR': 'concurrent resolution',
                      'HCM': 'concurrent memorial',
                      'HJR': 'joint resolution',
                      #'MIS': 'miscelanious' currently ignoring these odd ones
                  }
        try:
            return bill_types[bill_id]
        except KeyError:
            self.log("unkown bill type: " + bill_id)
            return 'bill'
        
    def scrape_bill(self, chamber, session, bill_id):
        session_id = self.get_session_id(session)
        url = base_url + 'DocumentsForBill.asp?Bill_Number=%s&Session_ID=%s' % (
                                                            bill_id, session_id)
        with self.urlopen(url) as docs_for_bill:
            root = html.fromstring(docs_for_bill)
            bill_title = root.xpath(
                            '//div[@class="ContentPageTitle"]')[1].text.strip()
            b_type = self.get_bill_type(bill_id[:-4])
            # Depending on the progress the bill has made through the house
            # some table might not exist, the links that have javascript:Show****
            # have a table with related documents/calanders/agendas/versions
            # I am skipping the sponsors link because that information is on the
            # bill overview page where all of the actions are found.
            doc_section_links = root.xpath(
                                    '//a[contains(@href, "javascript:Show")]')
            bill = Bill(session, chamber, bill_id, bill_title, type=b_type)
            bill.add_source(url)
            for link in doc_section_links:
                link_id = utils.parse_link_id(link)
                link_text = link.text_content().strip()
                div_path = '//div[@id="%s"]/table//tr' % link_id
                if link_text == 'Show Versions':
                    # the first row has only a comment
                    for tr in root.xpath(div_path)[1:]:
                        tds = tr.cssselect('td') # list(tr.iterchildren('td'))
                        if len(tds) >= 4:
                            bill_version = tds[1].text_content().strip()
                            bill_html = tds[2].xpath('string(font/a/@href)')
                            bill_pdf = tds[3].xpath('string(font/a/@href)')
                            bill.add_version(bill_version, 
                                                    bill_html, pdf_url=bill_pdf)
                elif link_text == 'Show Summaries/Fact Sheets':
                    for tr in root.xpath(div_path)[1:]:
                        # the first row has only a comment
                        tds = tr.cssselect('td')
                        if len(tds) > 1:
                            fact_sheet = tds[1].text_content().strip()
                            fact_sheet_url = tds[1].xpath(
                                                        'string(font/a/@href)')
                            bill.add_document(fact_sheet,
                                             fact_sheet_url, type="fact sheet")
                elif link_text in ('Show Senate Agendas', 'Show House Agendas'):
                    agenda_type = 'House Agenda' if re.search('House', link_text) else 'Senate Agenda'
                    for tr in root.xpath(div_path)[2:]:
                        # the first row has only a comment
                        # the second row is the table header
                        tds = tr.cssselect('td')
                        if len(tds) >= 8:
                            agenda_committee = tds[0].text_content().strip()
                            agenda_revised = tds[1].text.strip()
                            agenda_cancelled = tds[2].text.strip()
                            agenda_date = tds[3].text_content().strip()
                            agenda_time = tds[4].text_content().strip()
                            agenda_room = tds[5].text_content().strip()
                            agenda_pdf = tds[6].xpath('string(a/@href)').strip()
                            agenda_html = tds[7].xpath('string(a/@href)').strip()
                            bill.add_document(agenda_committee, 
                                                agenda_html, type=agenda_type)
                elif link_text in ('Show Senate Calendars', 'Show House Calendars'):
                    cal_type = 'house calendar' if re.match('House', link_text) else 'senate calendar'
                    for tr in root.xpath(div_path)[2:]:
                        # the first row has only a comment
                        # the second row is the table header
                        tds = tr.cssselect('td')
                        if len(tds) >= 6:
                            calendar_name = tds[0].text_content().strip()
                            calendar_number = tds[1].text_content().strip()
                            calendar_modified = True if tds[2].xpath('img') else False 
                            calendar_date = tds[3].text_content().strip()
                            calendar_html = tds[5].xpath('string(a/@href)')
                            bill.add_document(calendar_name, 
                                                calendar_html, type="calendar")
                elif link_text == 'Show Adopted Amendments':
                    for tr in root.xpath(div_path)[1:]:
                        tds = tr.cssselect('td')
                        amendment_title = tds[1].text_content().strip()
                        amendment_link = tds[2].xpath('string(font/a/@href)')
                        bill.add_document(amendment_title, 
                                            amendment_link, type='amendment')        
                elif link_text == 'Show Proposed Amendments':
                    for tr in root.xpath(div_path)[1:]:
                        tds = tr.cssselect('td')
                        if len(tds) >= 3: 
                            amendment_title = tds[1].text_content().strip()
                            amendment_link = tds[2].xpath('string(font/a/@href)')
                            bill.add_document(amendment_title,
                                               amendment_link, type='amendment')        
                elif link_text == 'Show Bill Videos':
                    for tr in root.xpath(div_path)[2:]:
                        tds = tr.cssselect('td')
                        if len(tds) >= 3:
                            video_title = tds[1].text_content().strip()
                            video_link = tds[2].xpath('string(a/@href)')
                            video_date = tds[0].text_content().strip()
                            bill.add_document(video_title, video_link, 
                                                date=video_date, type='video')

        # action_url = 'http://www.azleg.gov/FormatDocument.asp?inDoc=/legtext/49leg/2r/bills/hb2001o.asp'
        # again the actions page may or may not have a given table and the order
        # of the actions depends on the chamber the bill originated in. 
        ses_num = utils.legislature_to_number(session)
        action_url = base_url + 'FormatDocument.asp?inDoc=/legtext/%s/bills/%so.asp' % (ses_num, bill_id.lower())
        with self.urlopen(action_url) as action_page:
            bill.add_source(action_url)
            root = html.fromstring(action_page)
            action_tables = root.xpath('/html/body/div/table/tr[3]/td[4]/table/tr/td/table/tr/td/table')
            for table in action_tables:
                rows = table.cssselect('tr')
                house = False if chamber == 'upper' else True
                action = table.cssselect('td')[0].text_content().strip()[:-1]
                if action == 'SPONSORS':
                    sponsors = table.xpath('//sponsor')
                    for sponsor in sponsors:
                        name = sponsor.text.strip()
                        s_type = sponsor.getparent().getparent().getnext().text_content().strip()
                        bill.add_sponsor(s_type, name)
                elif action == 'COMMITTEES':
                    # the html for this table has meta tags that give the chamber
                    # and the committee abreviation
                    # <meta name="HCOMMITTEE" content="RULES">
                    # question for actions: in the case of committees would House
                    # Rules be better for an actor? 
                    for row in rows[1:]:
                        tds = row.cssselect('td')
                        meta_tag = row.cssselect('meta')[0]
                        actor = "%s:%s" % (meta_tag.get('name'), meta_tag.get('content'))
                        committee = meta_tag.get('content')
                        act = 'committee:reffered'
                        date = datetime.datetime.strptime(tds[1].text_content().strip(), '%m/%d/%y')
                        bill.add_action(actor, act, date, type='committee:referred')
                        if len(tds) == 5:
                            if re.match('\d{2}/\d{2}/\d{2}', tds[3].text_content().strip()):
                                date = datetime.datetime.strptime(tds[3].text_content().strip(), '%m/%d/%y')
                            else:
                                date = datetime.datetime.strptime(tds[1].text_content().strip(), '%m/%d/%y')
                            act = tds[4].text_content().strip()
                            status = 'other'
                            bill.add_action(actor, act, date, type=status, status=status)
                        elif len(tds) == 6:
                            where, committee = actor.split(':')
                            where = 'lower' if where == 'HCOMMITTEE' else 'upper'
                            date = datetime.datetime.strptime(tds[3].text_content().strip(), '%m/%d/%y')
                            vote = tds[4].text_content().strip()[1:-1]
                            if len(vote.split('-')) == 4:
                                yes, no, nv, exc = vote.split('-')
                            else:
                                yes, no, excused, absent, nv = vote.split('-')
                            motion = tds[5].text_content().strip()
                            passed = True if yes > no else False
                            vote = Vote(where, date, motion, passed, int(yes), int(no), int(nv), committee=committee)
                            vote.add_source(tds[0].xpath('string(a/@href)').strip())
                            
                            bill.add_vote(vote)
                elif action in ('HOUSE FIRST READ', 'HOUSE SECOND READ'):
                    aType = 'other'
                    if re.search('HOUSE FIRST', action):
                        aType = 'committee:referred'
                    bill.add_action('lower', action, utils.get_date(rows[0][1]),
                                     type=aType)
                elif action in ('SENATE FIRST READ', 'SENATE SECOND READ'):
                    aType = 'other'
                    if re.search('SECOND', action):
                        aType = 'committee:referred'
                    bill.add_action('upper', action, utils.get_date(rows[0][1]),
                                     type=aType)
                elif action in ('TRANSMIT TO HOUSE', 'TRANSMIT TO SENATE'):
                    actor = 'lower' if re.match('HOUSE', action) else 'upper'
                    house = True if actor == 'lower' else False
                    date = utils.get_date(rows[0][1])
                    bill.add_action(actor, action, date)
                elif re.match('COW ACTION \d', action):
                    actor = 'lower' if house else 'upper'
                    for row in rows[1:]:
                        date = utils.get_date(row[1])
                        bill.add_action(actor, action, date, motion=row[2].text_content().strip())
                elif action in ('HOUSE FINAL READ', 'SENATE FINAL READ', 'THIRD READ'):
                    actor = 'lower' if house else 'upper'
                    for row in rows[1:]:
                        if row[0].text_content().strip() == 'Vote Detail':
                            if len(row.getchildren()) == 10:
                                detail, date, ayes, nays, nv, exc, emer, rfe, two_thirds, result = [ x.text_content().strip() for x in row ]
                                passed = True if result == 'PASSED' else False
                                motion = action
                                date = datetime.datetime.strptime(date, '%m/%d/%y') if date else ''
                                vote = Vote(actor, date, motion, passed, int(ayes), int(nays), int(nv),
                                             excused=int(exc), emergency=emer,  rfe=rfe, 
                                             two_thirds_vote=two_thirds, type="passage")
                                vote.add_source(row[0].xpath('string(a/@href)').strip())
                                bill.add_vote(vote)
                            elif len(row.getchildren()) == 11:
                                detail, date, ayes, nays, nv, exc, emer, amend, rfe, two_thirds, result = [ x.text_content().strip() for x in row ]
                                passed = True if result == 'PASSED' else False
                                motion = action
                                date = datetime.datetime.strptime(date, '%m/%d/%y') if date else ''
                                vote = Vote(actor, date, motion, passed, int(ayes), int(nays), int(nv),
                                             excused=int(exc), emergency=emer, amended=amend,
                                              rfe=rfe, two_thirds_vote=two_thirds, type="passage")
                                vote.add_source(row[0].xpath('string(a/@href)').strip())
                                bill.add_vote(vote)
                        
                elif action == 'TRANSMITTED TO':
                    actor = 'lower' if house else 'upper'
                    act = action + ": " + rows[0][1].text_content().strip()
                    date = rows[0][2].text_content().strip()
                    date = datetime.datetime.strptime(date, '%m/%d/%y')
                    bill.add_action(actor, act, date, type='governor:received')
                    # need action and chaptered, chaptered version if they exists
                    act, date, chapter, version = '', '', '', ''
                    for row in rows[1:]:
                        if row[0].text_content().strip() == 'ACTION:':
                            act = row[1].text_content().strip()
                            date = datetime.datetime.strptime(row[2].text_content().strip(), '%m/%d/%y')
                        elif row[0].text_content().strip() == 'CHAPTER':
                            chapter = row[1].text_content().strip()
                        elif row[0].text_content().strip() == 'CHAPTERED VERSION':
                            version = row[1].text_content.strip()
                    if act:
                        action_type = 'governor:signed' if act == 'SIGNED' else 'governor:vetoed'
                        if chapter:
                            bill.add_action('governor', act, date, 
                                            type=action_type, chapter=chapter, 
                                            chaptered_version=version)
                        else:
                            bill.add_action('governor', act, date, 
                                                type=action_type)
        self.save_bill(bill)
        self.log("saved: " + bill['bill_id'])
                
    def scrape(self, chamber, session):
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod
            
        chamber_letter = {'lower': 'H', 'upper': 'S'}[chamber]
        view = {'lower':'allhouse', 'upper':'allsenate'}[chamber]
        url = base_url + 'Bills.asp?view=%s&Session_ID=%s'
        
        with self.urlopen(url % (view, session_id)) as bills_index:
                root = html.fromstring(bills_index)
                bill_links = root.xpath('//div/table/tr[3]/td[4]/table/tr/td/' +
                            'table[2]/tr[2]/td/table/tr/td[2]/table/tr/td//a')
                for link in bill_links:
                    bill_id = link.text.strip()
                    self.scrape_bill(chamber, session, bill_id)
