import re

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from . import utils
from .action_utils import get_action_type, get_verbose_action

from lxml import html

BASE_URL = 'http://www.azleg.gov/'

# map to type and official_type (maybe we can figure out PB/PZ and add names
SPONSOR_TYPES = {'P': ('primary', 'P'),
                 'C': ('cosponsor', 'C'),
                 'PB': ('primary', 'PB'),
                 'PZ': ('primary', 'PZ'),
                 'CZ': ('cosponsor', 'CZ')}

# This string of hot garbage appears when a document hasn't been posted yet.
hot_garbage_404_fail = ('The Requested Document Has Not Been '
                        'Posted To The Web Site Yet.'
                        '|There Are No Documents For [A-Z\d]+'
                        '|The page cannot be displayed because an internal server error has occurred.')

class AZBillScraper(BillScraper):
    def accept_response(self, response):
        normal = super(AZBillScraper, self).accept_response(response)
        return normal or response.status_code == 500

    """
    Arizona Bill Scraper.
    """
    jurisdiction = 'az'
    def get_session_id(self, session):
        """
        returns the session id for a given session
        """
        return self.metadata['session_details'][session]['session_id']

    def scrape_bill(self, chamber, session, bill_id):
        """
        Scrapes documents, actions, vote counts and votes for
        a given bill.
        """
        session_id = self.get_session_id(session)
        url = BASE_URL + 'DocumentsForBill.asp?Bill_Number=%s&Session_ID=%s' % (
                                           bill_id.replace(' ', ''), session_id)

        docs_for_bill = self.get(url).text

        if re.search(hot_garbage_404_fail, docs_for_bill):
            # Bailing here will prevent the bill from being saved, which
            # occurs in the scrape_actions method below.
            return

        root = html.fromstring(docs_for_bill)
        bill_title = root.xpath(
                        '//div[@class="ContentPageTitle"]')[1].text.strip()
        b_type = utils.get_bill_type(bill_id)
        bill = Bill(session, chamber, bill_id, bill_title, type=b_type)
        bill.add_source(url)
        path = '//tr[contains(td/font/text(), "%s")]'
        link_path = '//tr[contains(td/a/@href, "%s")]'
        link_path2 = '//tr[contains(td/font/a/@href, "%s")]'
        # versions
        for href in root.xpath("//a[contains(@href, 'pdf')]"):
            version_url = href.attrib['href']
            if "bills" in version_url.lower():
                name = list(href.getparent().getparent().getparent())
                name = name[1].text_content()
                bill.add_version(href.text_content(), version_url,
                                 on_duplicate='use_old',
                                 mimetype='application/pdf')

        #fact sheets and summary
        rows = root.xpath(link_path2 % '/summary/')
        for row in rows:
            tds = row.xpath('td')
            fact_sheet = tds[1].text_content().strip()
            fact_sheet_url = tds[1].xpath('string(font/a/@href)') or \
                             tds[2].xpath('string(font/a/@href)')
            bill.add_document(fact_sheet, fact_sheet_url, type="summary")

        #agendas
        # skipping revised, cancelled, date, time and room from agendas
        # but how to get the agenda type cleanly? meaning whether it is
        # house or senate?
        rows = root.xpath(link_path % '/agendas')
        for row in rows:
            tds = row.xpath('td')
            agenda_committee = tds[0].text_content().strip()
            agenda_html = tds[7].xpath('string(a/@href)').strip()
            if agenda_html == '':
                agenda_html = tds[6].xpath('string(a/@href)').strip()
            bill.add_document(agenda_committee, agenda_html)

        # House Calendars
        # skipping calendar number, modified, date
        rows = root.xpath(link_path % '/calendar/h')
        for row in rows:
            tds = row.xpath('td')
            calendar_name = tds[0].text_content().strip()
            calendar_html = tds[5].xpath('string(a/@href)')
            bill.add_document(calendar_name, calendar_html,
                              type='house calendar')
        # Senate Calendars
        # skipping calendar number, modified, date
        rows = root.xpath(link_path % '/calendar/s')
        for row in rows:
            tds = row.xpath('td')
            calendar_name = tds[0].text_content().strip()
            calendar_html = tds[5].xpath('string(a/@href)')
            bill.add_document(calendar_name, calendar_html,
                              type='senate calendar')
        # amendments
        rows = root.xpath(path % 'AMENDMENT:')
        for row in rows:
            tds = row.xpath('td')
            amendment_title = tds[1].text_content().strip()
            amendment_link = tds[2].xpath('string(font/a/@href)')

            if amendment_link == "": #if there's no html link, take the pdf one which is next
                amendment_link = tds[3].xpath('string(font/a/@href)')

            if amendment_link:
                bill.add_document(amendment_title, amendment_link,
                    type='amendment')

        # videos
        # http://azleg.granicus.com/MediaPlayer.php?view_id=13&clip_id=7684
        rows = root.xpath(link_path % '&clip_id')
        for row in rows:
            tds = row.xpath('td')
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
        bill_id = bill['bill_id'].replace(' ', '')
        action_url = BASE_URL + 'FormatDocument.asp?inDoc=/legtext/%s/bills/%so.asp' % (ses_num, bill_id.lower())
        action_page = self.get(action_url).text

        if re.search(hot_garbage_404_fail, action_page):
            # This bill has no actions yet, but that
            # happened frequently with pre-filed bills
            # before the 2013 session, so skipping probably
            # isn't the thing to do.
            self.save_bill(bill)
            return
        bill.add_source(action_url)
        root = html.fromstring(action_page)
        base_table = root.xpath('//table[@class="ContentAreaBackground"]')[0]
        # common xpaths
        table_path = '//table[contains(tr/td/b/text(), "%s")]'

        #sponsors
        sponsors = base_table.xpath('//sponsor')
        for sponsor in sponsors:
            name = sponsor.text.strip()
            # sponsor.xpath('string(ancestor::td[1]/following-sibling::td[1]/text())').strip()
            s_type = sponsor.getparent().getparent().getnext().text_content().strip()
            s_type, o_type = SPONSOR_TYPES[s_type]
            bill.add_sponsor(s_type, name, official_type=o_type)

        #titles
        table = base_table.xpath(table_path % 'TITLE')
        if table:
            for row in table[0].iterchildren('tr'):
                title = row[1].text_content().strip()
                if title != bill['title']:
                    bill.add_title(title)

        for table in base_table.xpath('tr/td/table') + root.xpath('//td[@align="left"]/table[not(@class="ContentAreaBackground")]'):
            action = table.xpath('string(tr[1]/td[1])').strip()
            if action == '':
                action = table.xpath('string(tr[1])').strip()
            if (action.endswith('FIRST READ:') or
                action.endswith('SECOND READ:') or 'WAIVED' in action):

                rows = table.xpath('tr')
                for row in rows:
                    action = row[0].text_content().strip()[:-1]
                    actor = 'lower' if action.startswith('H') else 'upper'
                    date = utils.get_date(row[1])
                    # bill:introduced
                    if (action.endswith('FIRST READ') or
                        action.endswith('FIRST WAIVED')):
                        if actor == chamber:
                            a_type = ['bill:introduced', 'bill:reading:1']
                        else:
                            a_type = 'bill:reading:1'
                        bill.add_action(actor, action, date, type=a_type)
                    else:
                        a_type = 'bill:reading:2'
                        bill.add_action(actor, action, date, type=a_type)
                continue

            elif action == 'COMMITTEES:':
                # committee assignments
                rows = table.xpath('tr')[1:]
                for row in rows:
                    # First add the committee assigned action
                    meta_tag = row.xpath('.//meta')[0]
                    h_or_s = meta_tag.get('name')[0] # @name is HCOMMITTEE OR SCOMMITTEE
                    committee = meta_tag.get('content') # @content is committee abbrv
                    #actor is house or senate referring the bill to committee
                    actor = 'lower' if h_or_s.lower() == 'h' else 'upper'
                    act = 'assigned to committee: ' + \
                        utils.get_committee_name(committee, actor)
                    date = utils.get_date(row[1])
                    bill.add_action(actor, act, date, type='committee:referred')
                    # now lets see if there is a vote
                    vote_url = row[0].xpath('string(a/@href)')
                    if vote_url:
                        date = utils.get_date(row[3])
                        try:
                            act = row[5].text_content().strip()
                        except IndexError:
                            #not sure what to do if action is not specified
                            #skipping and throwing a warning for now
                            self.logger.warning("Vote has no action, skipping.")
                            continue

                        a_type = get_action_type(act, 'COMMITTEES:')
                        act = get_verbose_action(act)
                        bill.add_action(actor,
                                        utils.get_committee_name(committee, actor) + ":" + act,
                                        date, type=a_type, abbrv=committee)
                        self.scrape_votes(actor, vote_url, bill, date,
                                            motion='committee: ' + act,
                                            committees=committee,
                                            type='other')
                    elif len(row) == 5:
                        # probably senate rules committee
                        date = utils.get_date(row[3])
                        if date == '':
                            date = utils.get_date(row[1])
                        act = row[4].text_content().strip()
                        a_type = get_action_type(act, 'COMMITTEES:')
                        act = get_verbose_action(act)
                        bill.add_action(actor,
                                        utils.get_committee_name(
                                            committee, actor) +
                                        ":" + act, date,
                                        type=a_type, abbrv=committee)
                continue

            elif 'CAUCUS' in action:
                rows = table.xpath('tr')[0:2]
                for row in rows:
                    actor = utils.get_actor(row, chamber)
                    action = row[0].text_content().strip()
                    if action.endswith(':'):
                        action = action[:-1]
                    if len(row) != 3:
                        self.warning('skipping row: %s' %
                                     row.text_content())
                        continue
                    result = row[2].text_content().strip()
                    # majority caucus Y|N
                    action = action + " recommends to concur: " + result
                    date = utils.get_date(row[1])
                    bill.add_action(actor, action, date, concur=result,
                                    type='other')
                continue

        # transmit to house or senate
            elif 'TRANSMIT TO' in action:
                rows = table.xpath('tr')
                for row in rows:
                    action = row[0].text_content().strip()[:-1]
                    actor = 'upper' if action.endswith('HOUSE') else 'lower'
                    date = utils.get_date(row[1])
                    bill.add_action(actor, action, date, type='other')
                continue

            # Committee of the whole actions
            elif 'COW ACTION' in action:
                rows = table.xpath('tr')
                actor = utils.get_actor(rows[0], chamber)
                if 'SIT COW ACTION' in action:
                    act = rows[0][-1].text_content().strip()
                    date = utils.get_date(rows[0][1])
                else:
                    act = rows[1][2].text_content().strip()
                    date = utils.get_date(rows[1][1])
                action = action + " " + get_verbose_action(act) # COW ACTION 1 DPA
                bill.add_action(actor, action, date, type='other')
                if len(rows) > 1 and rows[1][0].text_content().strip() == 'Vote Detail':
                    vote_url = rows[1][0].xpath('string(a/@href)')
                    self.scrape_votes(actor, vote_url, bill, date,
                                            motion=action, type='other',
                                            extra=act)
                continue
            # AMENDMENTS
            elif 'AMENDMENTS' in action:
                rows = table.xpath('tr')[1:]
                for row in rows:
                    act = row.text_content().strip()
                    if act == '':
                        continue
                    if 'passed' in act or 'adopted' in act:
                        a_type = 'amendment:passed'
                    elif 'failed' in act:
                        a_type = 'amendment:failed'
                    elif 'withdrawn' in act:
                        a_type = 'amendment:withdrawn'
                    else:
                        a_type = 'other'
                    # actor and date will same as previous action
                    bill.add_action(actor, act, date, type=a_type)
                continue
        # CONFERENCE COMMITTEE
        # http://www.azleg.gov/FormatDocument.asp?inDoc=/legtext/49Leg/2r/bills/hb2083o.asp

            # MISCELLANEOUS MOTION

            # MOTION TO RECONSIDER
            elif action == 'MOTION TO RECONSIDER:':
                date = utils.get_date(table[1][1])
                if date:
                    if table[1][0].text_content().strip() == 'Vote Detail':
                        vote_url = table[1][0].xpath('string(a/@href)')
                        bill.add_action(actor, action, date, type=a_type)
                        self.scrape_votes(actor, vote_url, bill, date,
                                          motion='motion to reconsider',
                                            type='other')
                    else:
                        action = table[-1][1].text_content().strip()
                        bill.add_action(actor, action, date, type='other')
                continue

            elif (action.endswith('FINAL READ:') or
                  action.endswith('THIRD READ:')):
                # house|senate final and third read
                rows = table.xpath('tr')
                # need to find out if third read took place in house or senate
                # if an ancestor table contains 'TRANSMIT TO' then the action
                # is taking place in that chamber, else it is in chamber
                actor = utils.get_actor(rows[0], chamber)
                # get a dict of keys from the header and values from the row
                k_rows = utils.get_rows(rows[1:], rows[0])
                action = rows[0][0].text_content().strip()
                for row in k_rows:
                    a_type = [get_action_type(action, 'Generic')]
                    if row[action].text_content().strip() == 'Vote Detail':
                        vote_url = row.pop(action).xpath('string(a/@href)')
                        vote_date = utils.get_date(row.pop('DATE'))
                        try:
                            passed = row.pop('RESULT').text_content().strip()
                        except KeyError:
                            passed = row.pop('2/3 VOTE').text_content().strip()

                        # leaves vote counts, ammended, emergency, two-thirds
                        # and possibly rfe left in k_rows. get the vote counts
                        # from scrape votes and pass ammended and emergency
                        # as kwargs to sort them in scrap_votes
                        pass_fail = {'PASSED': 'bill:passed',
                                        'FAILED': 'bill:failed'}[passed]
                        a_type.append(pass_fail)
                        bill.add_action(actor, action, vote_date,
                                        type=a_type)
                        row['type'] = 'passage'
                        self.scrape_votes(actor, vote_url, bill, vote_date,
                                            passed=passed, motion=action,
                                            **row)
                    else:
                        date = utils.get_date(row.pop('DATE'))
                        if date:
                            bill.add_action(actor, action, date, type=a_type)
                continue
            elif 'TRANSMITTED TO' in action:
                # transmitted to Governor or secretary of the state
                # SoS if it goes to voters as a proposition and memorials, etc
                rows = table.xpath('tr')
                actor = utils.get_actor(rows[0], chamber)
                # actor is the actor from the previous statement because it is
                # never transmitted to G or S without third or final read
                sent_to = rows[0][1].text_content().strip()
                date = utils.get_date(rows[0][2])
                a_type = 'governor:received' if sent_to[0] == 'G' else 'other'
                bill.add_action(actor, "TRANSMITTED TO " + sent_to, date,
                                type=a_type)
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
                    a_type = 'governor:signed' if act == 'SIGNED' else 'governor:vetoed'
                    if chapter:
                        bill.add_action(sent_to.lower(), act, date,
                                        type=a_type, chapter=chapter,
                                        chaptered_version=version)
                    else:
                        bill.add_action(sent_to.lower(), act, date,
                                            type=a_type)
                continue

        # this is probably only important for historical legislation
            elif 'FINAL DISPOSITION' in action:
                rows = table.xpath('tr')
                if rows:
                    disposition = rows[0][1].text_content().strip()
                    bill['final_disposition'] = disposition
        bill = self.sort_bill_actions(bill)
        self.save_bill(bill)

    def scrape(self, chamber, session):
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)
        view = {'lower':'allhouse', 'upper':'allsenate'}[chamber]
        url = BASE_URL + 'Bills.asp?view=%s&Session_ID=%s' % (view, session_id)

        bills_index = self.get(url).text
        root = html.fromstring(bills_index)
        bill_links = root.xpath('//div/table/tr[3]/td[4]/table/tr/td/' +
                    'table[2]/tr[2]/td/table/tr/td[2]/table/tr/td//a')
        for link in bill_links:
            bill_id = link.text.strip()
            bill_id = " ".join(re.split('([A-Z]*)([0-9]*)', bill_id)).strip()
            self.scrape_bill(chamber, session, bill_id)

    def scrape_votes(self, chamber, url, bill, date, **kwargs):
        """
        Scrapes the votes from a vote detail page with the legislator's names
        this handles all of the votes and expects the following keyword
        arguments: motion
        an Arizona Vote object will have the following additional fields:
        additional vote counts:
            +not_voting, +excused, +absent, +present
        additional vote lists
            +NV, +EX, +AB, +P
        this depends on the chamber and the committee
        """
        o_args = {}
        passed = '' # to test if we need to compare vote counts later
        v_type = kwargs.pop('type')
        if 'passed' in kwargs:
            passed = {'PASSED': True, 'FAILED': False}[kwargs.pop('passed')]
        if 'AMEND' in kwargs:
            o_args['amended'] = kwargs.pop('AMEND').text_content().strip()
        if 'motion' in kwargs:
            motion = kwargs.pop('motion')
        if 'EMER' in kwargs and kwargs['EMER'].text_content().strip():
            o_args['EMER'] = kwargs.pop('EMER').text_content().strip()
        if '2/3 VOTE' in kwargs and kwargs['2/3 VOTE'].text_content().strip():
            o_args['2/3 VOTE'] = kwargs.pop('2/3 VOTE').text_content().strip()
        if 'committee' in kwargs:
            o_args['committee'] = utils.get_committee_name(kwargs.pop('committee'),
                                                            chamber)
        if 'committees' in kwargs:
            o_args['committee'] = utils.get_committee_name(kwargs.pop('committees'),
                                                            chamber)
        vote_page = self.get(url).text
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
                o_count += int(v)
        if passed == '':
            passed = yes_count > no_count
            if ('committee' not in o_args) and ('committees' not in o_args):
                if chamber == 'upper' and passed:
                    if 'EMER' in o_args or '2/3 VOTE' in o_args:
                        passed = yes_count > 20
                    else:
                        passed = yes_count > 16
                elif chamber == 'lower' and passed:
                    if 'EMER' in o_args or '2/3 VOTE' in o_args:
                        passed = yes_count > 40
                    else:
                        passed = yes_count > 31

        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    o_count, type=v_type, **o_args)
        vote.add_source(url)
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
                if v in vote:
                    vote[v].append(name)
                else:
                    vote[v] = [name]
                vote.other(name)

        # Warn if the stated other_vote count doesn't add up.
        if vote['other_count'] != len(vote['other_votes']):
            self.warning("Other votes count on webpage didn't match "
                         "len(other_votes)...using length instead.")
            vote['other_count'] = len(vote['other_votes'])

        bill.add_vote(vote)

    def sort_bill_actions(self, bill):
        actions = bill['actions']
        actions_list = []
        out_of_order = []
        new_list = []
        if not actions:
            return bill
        action_date = actions[0]['date']
        actions[0]['action'] = actions[0]['action'].lower()
        actions_list.append(actions[0])
        # seperate the actions that are out of order
        for action in actions[1:]:
            if action['date'] < action_date:
                out_of_order.append(action)
            else:
                actions_list.append(action)
                action_date = action['date']
            action['action'] = action['action'].lower()
        action_date = actions_list[0]['date']


        for action in actions_list:
            # this takes care of the actions in beween
            for act in out_of_order:
                if act['date'] < action_date:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))
                if act['date'] >= action_date and act['date'] < action['date']:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))
            new_list.append(action)

            for act in out_of_order:
                if act['date'] == action['date']:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))

        if out_of_order != []:
            self.log("Unable to sort " + bill['bill_id'])
            return bill
        else:
            bill['actions'] = new_list
            return bill
