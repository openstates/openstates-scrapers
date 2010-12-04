import datetime, re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.az import utils

from lxml import html

BASE_URL = 'http://www.azleg.gov/'

class AZBillScraper(BillScraper):
    """
    Arizona Bill Scraper.
    """
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
                      'MIS': 'miscellaneous' # currently ignoring these odd ones
                  }
        try:
            return bill_types[bill_id]
        except KeyError:
            self.log('unknown bill type: ' + bill_id)
            return 'bill'
        
    def scrape_bill(self, chamber, session, bill_id):
        """
        Scrapes documents, actions, vote counts and votes for 
        a given bill.
        """
        session_id = self.get_session_id(session)
        url = BASE_URL + 'DocumentsForBill.asp?Bill_Number=%s&Session_ID=%s' % (
                                                            bill_id, session_id)
        with self.urlopen(url) as docs_for_bill:
            root = html.fromstring(docs_for_bill)
            bill_title = root.xpath(
                            '//div[@class="ContentPageTitle"]')[1].text.strip()
            b_type = self.get_bill_type(bill_id[:-4])
            bill = Bill(session, chamber, bill_id, bill_title, type=b_type)
            bill.add_source(url)
            path = '//tr[contains(td/font/text(), "%s")]'
            link_path = '//tr[contains(td/a/@href, "%s")]'
            link_path2 = '//tr[contains(td/font/a/@href, "%s")]'
            # versions
            rows = root.xpath(path % 'd Version')
            for row in rows:
                tds = row.cssselect('td')
                bill_version = tds[1].text_content().strip()
                bill_html = tds[2].xpath('string(font/a/@href)')
                bill.add_version(bill_version, bill_html)
                                            
            #fact sheets and summary
            rows = root.xpath(link_path % '/summary/')
            for row in rows:
                tds = row.cssselect('td')
                fact_sheet = tds[1].text_content().strip()
                fact_sheet_url = tds[1].xpath('string(font/a/@href)')
                bill.add_document(fact_sheet, fact_sheet_url, type="summary")
                    
            #agendas
            # skipping revised, cancelled, date, time and room from agendas
            # but how to get the agenda type cleanly? meaning whether it is 
            # house or senate?
            rows = root.xpath(link_path2 % 'inDoc=/agendas')
            for row in rows:
                tds = row.cssselect('td')
                agenda_committee = tds[0].text_content().strip()
                agenda_html = tds[7].xpath('string(a/@href)').strip()
                bill.add_document(agenda_committee, agenda_html)
                
            # House Calendars
            # skipping calendar number, modified, date
            rows = root.xpath(link_path2 % '/calendar/h')
            for row in rows:
                tds = row.cssselect('td')
                calendar_name = tds[0].text_content().strip()
                calendar_html = tds[5].xpath('string(a/@href)')
                bill.add_document(calendar_name, calendar_html, 
                                  type='house calendar')
            # Senate Calendars
            # skipping calendar number, modified, date
            rows = root.xpath(link_path2 % '/calendar/s')
            for row in rows:
                tds = row.cssselect('td')
                calendar_name = tds[0].text_content().strip()
                calendar_html = tds[5].xpath('string(a/@href)')
                bill.add_document(calendar_name, calendar_html, 
                                  type='senate calendar')
            # amendments
            rows = root.xpath(path % 'AMENDMENT:')
            for row in rows:
                tds = row.cssselect('td')
                amendment_title = tds[1].text_content().strip()
                amendment_link = tds[2].xpath('string(font/a/@href)')
                bill.add_document(amendment_title, amendment_link, type='amendment')
            
            # videos
            # http://azleg.granicus.com/MediaPlayer.php?view_id=13&clip_id=7684
            rows = root.xpath(link_path2 % '&clip_id')
            for row in rows:
                tds = row.cssselect('td')
                video_title = tds[1].text_content().strip()
                video_link = tds[2].xpath('string(a/@href)')
                video_date = tds[0].text_content().strip()
                bill.add_document(video_title, video_link, date=video_date, 
                                  type='video')
                
        self.scrape_actions(chamber, session, bill)    

    def scrape_actions(self, chamber, session, bill):
        """
        Scrape the actions for a given bill
        """
        ses_num = utils.legislature_to_number(session)
        bill_id = bill['bill_id']
        action_url = BASE_URL + 'FormatDocument.asp?inDoc=/legtext/%s/bills/%so.asp' % (ses_num, bill_id.lower())
        with self.urlopen(action_url) as action_page:
            bill.add_source(action_url)
            root = html.fromstring(action_page)
            base_table = root.xpath('//table[@class="ContentAreaBackground"]')[0]
            # common xpaths
            rows_path = '//tr[contains(td/b/text(), "%s")]/following-sibling::tr' 
            row_path = '//tr[contains(td/b/text(), "%s")]'
            table_path = '//table[contains(tr/td/b/text(), "%s")]'
            
            #sponsors
            sponsors = base_table.xpath('//sponsor')
            for sponsor in sponsors:
                name = sponsor.text.strip()
                # sponsor.xpath('string(ancestor::td[1]/following-sibling::td[1]/text())').strip()
                s_type = sponsor.getparent().getparent().getnext().text_content().strip()
                bill.add_sponsor(s_type, name)
                
            house = False if chamber == 'upper' else True # chamber flag
            
            # committee assignments
            rows = base_table.xpath(rows_path % 'COMMITTES:')
            #first row is the header
            for row in rows[1:]:
                # First add the committee assigned action
                meta_tag = row.cssselect('meta')[0]
                h_or_s = meta_tag.get('content')[0] # @name is HCOMMITTEE OR SCOMMITTEE
                committee = meta_tag.get('content') # @content is committee abbrv
                #actor is house or senate referring the bill to committee
                actor = 'lower' if h_or_s == 'H' else 'upper'
                act = 'assigned to committee'
                date = utils.get_date(row[1])
                bill.add_action(actor, act, date, type='committee:referred')
                # now lets see if there is a vote
                vote_url = row[0].xpath('string(a/@href)')
                if vote_url:
                    date = utils.get_date(row[3])
                    motion = utils.get_action(row[5].text_content().strip())
                    self.scrape_votes(vote_url, bill, actor, date,
                                        motion=motion, committee=committee)
                elif len(row) == 5:
                    # probably senate rules committee
                    # TODO need to translate the act to a type of committee:passed
                    # :failed |favorable|unfavorable
                    date = utils.get_date(row[3])
                    act = utils.get_action(row[4].text_content().strip())
                    bill.add_action(committee, act, date)
            
            # house|senate first|second read|waived
            rows = base_table.xpath(row_path % 'FIRST READ:')
            rows.extend(base_table.xpath(row_path % 'SECOND READ:'))
            rows.extend(base_table.xpath(row_path % 'WAIVED:'))
            for row in rows:
                action = row[0].text_content().strip()[:-1]
                h_or_s = 'lower' if action.startswith('H') else 'upper'
                a_type = 'other'
                date = utils.get_date(row[1])
                # bill:introduced
                if action.endswith('FIRST READ') and h_or_s == chamber:
                    a_type = 'bill:introduced'
                    bill.add_action(chamber, action, date, type=a_type)
                # committee:referred
                if action in ('HOUSE FIRST READ', 'SENATE SECOND READ'):
                    a_type = 'committee:referred'
                bill.add_action(h_or_s, action, date, type=a_type)
            # majority|minority caucus
            rows = base_table.xpath(row_path % 'CAUCUS')
            for x in range(len(rows)):
                h_or_s = chamber
                action = rows[x][0].text_content().strip()
                if action.endswith(':'):
                    action = action[:-1]
                result = rows[x][2].text_content().strip()
                date = utils.get_date(rows[x][1])
                if x >= 3:
                    h_or_s = {'upper':'lower', 'lower': 'upper'}[chamber]
                bill.add_action(h_or_s, action, date, concur=result, type='other')
            
            # transmit to house or senate
            rows = base_table.xpath(row_path % 'TRANSMIT TO')
            for row in rows:
                action = row[0].text_content().strip()[:-1]
                h_or_s = 'lower' if action.endswith('HOUSE') else 'upper'
                date = utils.get_date(rows[0][1])
                bill.add_action(h_or_s, action, date, type='other')
            
            # Committee of the whole actions
            tables = base_table.xpath(table_path % 'COW ACTION')
            for rows in [ table.xpath('tr') for table in tables ]:
                h_or_s = rows[0].xpath('ancestor::table[1]/preceding-sibling::' + 
                              'table/tr/td/b[contains(text(), "TRANSMIT TO")]')
                if h_or_s:
                    # actor is the first B element
                    h_or_s = h_or_s[0].text_content().strip()
                    actor = 'upper' if h_or_s.endswith('SENATE:') else 'lower'
                else:
                    actor = chamber
                action = rows[0][0].text_content().strip()
                if action == 'SIT COW ACTION:': # TODO figure out how to classify these
                    motion = utils.get_action(rows[0][3].text_content().strip())
                    date = utils.get_date(rows[0][1])
                else:
                    motion = utils.get_action(rows[1][2].text_content().strip())
                    date = utils.get_date(rows[1][1])
                if rows[1][0].text_content().strip() == 'Vote Detail':
                    vote_url = rows[1][0].xpath('string(a/@href)')
                    self.scrape_votes(actor, vote_url, bill, date, 
                                        motion=motion)
                else:
                    bill.add_action(actor, action, date, motion=motion)
            
            # house|senate final and third read
            tables = base_table.xpath(table_path % 'FINAL READ:')
            tables.extend(base_table.xpath(table_path % 'THIRD READ:'))
            for rows in [ table.xpath('tr') for table in tables ]:
                # need to find out if third read took place in house or senate
                # if an ancestor table contains 'TRANSMIT TO' then the action
                # is taking place in that chamber, else it is in chamber
                h_or_s = rows[0].xpath('ancestor::table[1]/preceding-sibling::' + 
                              'table/tr/td/b[contains(text(), "TRANSMIT TO")]')
                if h_or_s:
                    # actor is the first B element
                    h_or_s = h_or_s[0].text_content().strip()
                    actor = 'upper' if h_or_s[0].endswith('senate:') else 'lower'
                else:
                    actor = chamber
                # get a dict of keys from the header and values from the row
                k_rows = utils.get_rows(rows[1:], rows[0])
                action = rows[0][0].text_content().strip()
                if rows[1][0].text_content().strip() == 'Vote Detail':
                    vote_url = k_rows[0].pop(action).xpath('string(a/@href)')
                    vote_date = utils.get_date(k_rows[0].pop('DATE'))
                    passed = k_rows[0].pop('RESULT').text_content().strip()
                    # leaves vote counts, ammended, emergency, two-thirds
                    # and possibly rfe left in k_rows. get the vote counts 
                    # from scrape votes and pass ammended and emergency
                    # as kwargs to sort them in scrap_votes
                    self.scrape_votes(actor, vote_url, bill, vote_date,
                                      passed=passed, motion='passage', **k_rows[0])
                else:
                    date = utils.get_date(k_rows[0].pop('DATE'))
                    bill.add_action(actor, action, date)
            # transmitted to Governor or secretary of the state
            # SoS if it goes to voters as a proposition
            table = base_table.xpath(table_path % 'TRANSMITTED TO')
            # pretty sure there should only be one table
            if table:
                rows = table[0].xpath('tr')
                # actor is the actor from the previous statement because it is 
                # never transmitted to G or S without third or final read
                sent_to = rows[0][1].text_content().strip()
                date = utils.get_date(rows[0][2])
                action_type = 'governor:received' if sent_to[0] == 'G' else 'other'
                bill.add_action(actor, "TRNASMITTED TO " + sent_to, date, 
                                type=action_type)
                # See if the actor is the governor and whether he signed
                # the bill or vetoed it
                act, date, chapter, version = '', '', '', ''
                for row in rows[1:]:
                    if row[0].text_content().strip() == 'ACTION:':
                        act = row[1].text_content().strip()
                        date = utils.get_date(row[2])
                    elif row[0].text_content().strip() == 'CHAPTER:':
                        chapter = row[1].text_content().strip()
                    elif row[0].text_content().strip() == 'CHAPTERED VERSION:':
                        version = row[1].text_content().strip()
                    elif row[0].text_content().strip() == 'TRANSMITTED VERSION:':
                        version = row[1].text_content().strip()
                if act and sent_to == 'GOVERNOR':
                    action_type = 'governor:signed' if act == 'SIGNED' else 'governor:vetoed'
                    if chapter:
                        bill.add_action(sent_to.lower(), act, date, 
                                        type=action_type, chapter=chapter, 
                                        chaptered_version=version)
                    else:
                        bill.add_action(sent_to.lower(), act, date, 
                                            type=action_type)
                elif sent_to == 'SECRETARY OF STATE':
                    date = utils.get_date(rows[0][2])
                    bill.add_action(actor, 'transmitted to secratary of state',
                                    date, type='other', version=version) 
                    
        self.save_bill(bill)
                
    def scrape(self, chamber, session):
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)
        view = {'lower':'allhouse', 'upper':'allsenate'}[chamber]
        url = BASE_URL + 'Bills.asp?view=%s&Session_ID=%s' % (view, session_id)
        
        with self.urlopen(url) as bills_index:
            root = html.fromstring(bills_index)
            bill_links = root.xpath('//div/table/tr[3]/td[4]/table/tr/td/' +
                        'table[2]/tr[2]/td/table/tr/td[2]/table/tr/td//a')
            for link in bill_links:
                bill_id = link.text.strip()
                self.scrape_bill(chamber, session, bill_id)
                    
    def scrape_votes(self, chamber, url, bill, date, **kwargs):
        """
        Scrapes the votes from a vote detail page with the legislator's names
        """
        o_args = {}
        if 'passed' in kwargs:
            passed = kwargs.pop('passed')
            passed = {'PASSED': True, 'FAILED': False}[passed]
            o_args['type'] = 'passage'
        else:
            o_args['type'] = 'other'
        if 'AMEND' in kwargs:
            o_args['amended'] = kwargs.pop('AMEND').text_content().strip()
        if 'motion' in kwargs:
            motion = kwargs.pop('motion')
        with self.urlopen(url) as vote_page:
            root = html.fromstring(vote_page)
            vote_table = root.xpath('/html/body/div/table/tr[3]/td[4]/table/tr/td/table/tr/td/table')[0]
            vote_count = vote_table.xpath('following-sibling::p/following-sibling::text()')
            vote_string = vote_count[0].replace(u'\xa0', '').strip()
            v_count = re.compile(r'\b[A-Z]*\s*[A-z]*:\s\d*')
            v_list = v_count.findall(vote_string)
            o_count = 0
            for x in v_list:
                k, v = x.split(':')
                # make NOT VOTING not_voting
                k = k.strip().replace(' ', '_').lower()
                v = int(v.strip())
                if k == 'ayes':
                    yes_count = int(v)
                elif k == 'nays':
                    no_count = int(v)
                else:
                    o_args.update({str(k):v})
                    o_count = o_count + v
            if o_args['type'] == 'other':
                passed = yes_count > no_count
            vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                        o_count, **o_args)
            # grab all the tables descendant tds
            tds = vote_table.xpath('descendant::td')
            # pair 'em up
            matched = [ tds[y:y+2] for y in range(0, len(tds), 2) ]
            for name, v in iter(matched):
                v = v.text_content().strip()
                name = name.text_content().strip()
                if name == 'Member Name':
                    continue
                if v == 'Y':
                    vote.yes(name)
                elif v == 'N':
                    vote.no(name)
                else:
                    vote.other(name)
            bill.add_vote(vote)
