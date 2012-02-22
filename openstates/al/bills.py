from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import re
import datetime
import lxml.html

_action_re = (
    ('Introduced', 'bill:introduced'),
    ('(Forwarded|Delivered) to Governor', 'governor:received'),
    ('Amendment (?:.*)Offered', 'amendment:introduced'),
    ('Substitute (?:.*)Offered', 'amendment:introduced'),
    ('Amendment (?:.*)adopted', 'amendment:passed'),
    ('Amendment lost', 'amendment:failed'),
    ('Read for the first time and referred to',
       ['bill:reading:1', 'committee:referred']),
    ('(r|R)eferred to', 'committee:referred'),
    ('Read for the second time', 'bill:reading:2'),
    ('(S|s)ubstitute adopted', 'bill:substituted'),
    ('(m|M)otion to Adopt (?:.*)adopted', 'amendment:passed'),
    ('(m|M)otion to (t|T)able (?:.*)adopted', 'amendment:passed'),
    ('(m|M)otion to Adopt (?:.*)lost', 'amendment:failed'),
    ('(m|M)otion to Read a Third Time and Pass adopted', 'bill:passed'),
    ('(m|M)otion to Concur In and Adopt adopted', 'bill:passed'),
    ('Third Reading Passed', 'bill:passed'),
    ('Reported from', 'committee:passed'),
    ('Indefinitely Postponed', 'bill:failed'),
    ('Passed Second House', 'bill:passed'),
    # memorial resolutions can pass w/o debate
    ('Joint Rule 11', ['bill:introduced', 'bill:passed']),
    ('Lost in', 'bill:failed'),
    ('Favorable from', 'committee:passed:favorable'),
)

def _categorize_action(action):
    for pattern, types in _action_re:
        if re.findall(pattern, action):
            return types
    return 'other'

class ALBillScraper(BillScraper):

    state = 'al'

    def refresh_session(self):
        url = ('http://alisondb.legislature.state.al.us/acas/ACASLoginFire.asp'
               '?SESSION=%s') % self.session_id
        html = self.urlopen(url)

    def scrape(self, chamber, session):
        self.session_id = self.metadata['session_details'][session]['internal_id']
        self.base_doc_url = 'http://alisondb.legislature.state.al.us/acas/searchableinstruments/%s/PrintFiles/' % session

        chamber_piece = {'upper': 'Senate',
                         'lower': 'House+of+Representatives'}[chamber]
        # resolutions
        res_url = ('http://alisondb.legislature.state.al.us/acas/SESSResosBySe'
                   'lectedMatterTransResults.asp?WhichResos=%s&TransCodes='
                   '{All}&LegDay={All}') % chamber_piece
        self.scrape_for_bill_type(chamber, session, res_url)

        bill_url = ('http://alisondb.legislature.state.al.us/acas/SESSBillsByS'
                    'electedMatterTransResults.asp?TransCodes={All}'
                    '&LegDay={All}&WhichBills=%s') % chamber_piece
        self.scrape_for_bill_type(chamber, session, bill_url)


    def scrape_for_bill_type(self, chamber, session, url):

        self.refresh_session()

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            # bills are all their own table with cellspacing=4 (skip first)
            bill_tables = doc.xpath('//table[@cellspacing="4"]')
            for bt in bill_tables[1:]:

                # each table has 3 rows: detail row, description, blank
                details, desc, _ = bt.xpath('tr')

                # first <tr> has img, button, sponsor, topic, current house
                #   current status, committee, committee2, last action
                _, button, sponsor, subject, _, _, com1, com2, _ = details.xpath('td')

                # contains script tag that has a document.write that writes the
                # bill_id, we have to pull that out (gross, but only way)
                script_text = button.text_content()
                # skip SBIR/HBIR
                if 'SBIR' in script_text or 'HBIR' in script_text:
                    continue

                """ script text looks like:
                   document.write("<input type=button id=BTN71139 name=BTN71139 style='font-weight:normal' value='SB1'");
                   document.write(" onClick=\"javascript:instrumentSelected(this,'71139','SB1','ON','ON','ON','");
                   document.write(status + "','OFF','SB1-int.pdf,,','SB1-int.pdf,,')\">");
                """

                oid, bill_id, fnotes = re.findall(r"instrumentSelected\(this,'(\d+)','(\w+)','ON','ON','(ON|OFF)'",
                                                  script_text)[0]
                second_piece = re.findall(r"status \+ \"','(ON|OFF)','([^,]*),([^,]*),([^,]*)", script_text)
                if second_piece:
                    amend, intver, engver, enrver = second_piece[0]
                else:
                    intver = engver = enrver = None

                sponsor = sponsor.text_content()
                subject = subject.text_content()
                com1 = com1.text_content()
                com2 = com2.text_content()
                desc = desc.text_content()

                if 'B' in bill_id:
                    bill_type = 'bill'
                elif 'JR' in bill_id:
                    bill_type = 'joint resolution'
                elif 'R' in bill_id:
                    bill_type = 'resolution'

                # title is missing on a few bills
                title = desc.strip()
                if not title:
                    return

                # create bill
                bill = Bill(session, chamber, bill_id, title, type=bill_type)
                if subject:
                    bill['subjects'] = [subject]

                if fnotes == 'ON':
                    bill.add_document('fiscal notes', 'http://alisondb.legislature.state.al.us/acas/ACTIONFiscalNotesFrameMac.asp?OID=%s&LABEL=%s' %
                                      (oid, bill_id))

                self.get_sponsors(bill, oid)
                self.get_actions(bill, oid)

                # craft bill URLs
                if intver:
                    bill.add_version('introduced', self.base_doc_url + intver)
                if engver:
                    bill.add_version('engrossed', self.base_doc_url + engver)
                if enrver:
                    bill.add_version('enrolled', self.base_doc_url + enrver)

                self.save_bill(bill)


    def get_actions(self, bill, oid):
        url = 'http://alisondb.legislature.state.al.us/acas/ACTIONHistoryResultsMac.asp?OID=%s&LABEL=%s' % (oid, bill['bill_id'])

        bill.add_source(url)
        action_chamber = bill['chamber']

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for row in doc.xpath('//tr[@valign="top"]'):
                # date, amend/subst, matter, committee, nay, yea, abs, vote
                tds = row.xpath('td')

                # only change date if it exists (actions w/o date get old date)
                if tds[0].text_content():
                    date = datetime.datetime.strptime(tds[0].text_content(),
                                                      '%m/%d/%Y')

                amendment = tds[1].xpath('.//input/@value')
                if amendment:
                    amendment = amendment[0]
                    bill.add_document('amendment ' + amendment,
                                      self.base_doc_url + amendment + '.pdf')
                else:
                    amendment = None

                action = tds[2].text_content().strip()
                if ('Received in Senate' in action or
                    'referred to the Senate' in action):
                    action_chamber = 'upper'
                elif ('Recieved in House' in action or
                      'referred to the House' in action
                     ):
                    action_chamber = 'lower'

                if action:
                    atype = _categorize_action(action)
                    bill.add_action(action_chamber, action, date,
                                    type=atype, amendment=amendment)

                # pulling values out of javascript
                vote_button = tds[-1].xpath('input')
                if vote_button:
                    vote_js = vote_button[0].get('onclick')
                    moid, vote, body, inst = re.match(".*\('(\d+)','(\d+)','(\d+)','(\w+)'", vote_js).groups()
                    self.scrape_vote(bill, moid, vote, body, inst, action,
                                     action_chamber)



    def get_sponsors(self, bill, oid):
        url = "http://alisondb.legislature.state.al.us/acas/ACTIONSponsorsResultsMac.asp?OID=%s&LABEL=%s" % (oid, bill['bill_id'])

        bill.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            # primary sponsors
            for cs in doc.xpath('//table[2]/tr/td[1]/table/tr/td/text()'):
                if cs:
                    bill.add_sponsor('primary', cs)
            # cosponsors in really weird table layout (likely to break)
            for cs in doc.xpath('//table[2]/tr/td[2]/table/tr/td/text()'):
                if cs:
                    bill.add_sponsor('cosponsor', cs)


    def scrape_vote(self, bill, moid, vote_id, body, inst, motion, chamber):
        url = "http://alisondb.legislature.state.al.us/acas/GetRollCallVoteResults.asp?MOID=%s&VOTE=%s&BODY=%s&INST=%s&SESS=%s" % (
            moid, vote_id, body, inst, self.session_id)
        doc = lxml.html.fromstring(self.urlopen(url))

        voters = {'Y': [], 'N': [], 'P': [], 'A': []}

        leg_tds = doc.xpath('//td[@width="33%"]')
        for td in leg_tds:
            name = td.text
            two_after = td.xpath('following-sibling::td')[1].text
            if name == 'Total Yea:':
                total_yea = int(two_after)
            elif name == 'Total Nay:':
                total_nay = int(two_after)
            elif name == 'Total Abs:':
                total_abs = int(two_after)
            elif name == 'Legislative Date:':
                vote_date = datetime.datetime.strptime(two_after, '%m/%d/%Y')
            # lines to ignore
            elif name in ('Legislative Day:', 'Vote ID:'):
                pass
            elif 'Vacant' in name:
                pass
            else:
                # add legislator to list of voters
                voters[two_after].append(name)

        # TODO: passed is faked
        total_other = total_abs + len(voters['P'])
        vote = Vote(chamber, vote_date, motion, total_yea > total_nay,
                    total_yea, total_nay, total_other)
        vote.add_source(url)
        for member in voters['Y']:
            vote.yes(member)
        for member in voters['N']:
            vote.no(member)
        for member in (voters['A'] + voters['P']):
            vote.other(member)

        bill.add_vote(vote)
