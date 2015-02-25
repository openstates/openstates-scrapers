import datetime
import re
import time

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import lxml.html
import requests


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
    jurisdiction = 'al'
    CHAMBERS = {'H': 'lower', 'S': 'upper'}
    DATE_FORMAT = '%m/%d/%Y'

    # Due to a scrapelib bug, a requests Session is necessary to maintain cookies
    # Once this is fixed, roll back to vanilla scrapelib GETs and POSTs
    s = requests.Session()
    def sget(self, **request_args):
        time.sleep(1)
        self.log('Special GET request to {}'.format(request_args['url']))
        return self.s.get(**request_args)
    def spost(self, **request_args):
        time.sleep(1)
        self.log('Special POST request to {}'.format(request_args['url']))
        return self.s.post(**request_args)

    def scrape(self, session, chambers):
        # self.session = session
        self.session = '2011rs'
        self.session_name = self.metadata['session_details'][self.session]['_scraped_name']
        self.session_id = self.metadata['session_details'][self.session]['internal_id']

        SESSION_SET_URL = 'http://alisondb.legislature.state.al.us/Alison/ALISONLogin.aspx'
        RESOLUTION_TYPE_URL = ''
        RESOLUTION_LIST_URL = 'http://alisondb.legislature.state.al.us/Alison/SESSResList.aspx?STATUSCODES=Had%20First%20Reading%20House%20of%20Origin&BODY=999999'
        BILL_TYPE_URL = 'http://alisondb.legislature.state.al.us/Alison/SESSBillsBySelectedStatus.aspx'
        BILL_LIST_URL = 'http://alisondb.legislature.state.al.us/Alison/SESSBillsList.aspx?STATUSCODES=Had%20First%20Reading%20House%20of%20Origin&BODY=999999'

        # self.scrape_for_bill_type(session, res_url)

        # Activate an ASP.NET session, and set the legislative session
        doc = lxml.html.fromstring(self.sget(url=SESSION_SET_URL).text)
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        form = {
                '__EVENTTARGET': 'ctl00$cboSession',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                'ctl00$cboSession': self.session_name
                }
        self.spost(url=SESSION_SET_URL, data=form, allow_redirects=False)

        # With the ASP.NET session activated, acquire a list of bills
        doc = lxml.html.fromstring(self.sget(url=BILL_TYPE_URL).text)
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        form = {
                '__EVENTTARGET': 'ctl00$MainDefaultContent$gvStatus$ctl02$ctl00',
                '__EVENTARGUMENT': 'Select$0',
                '__LASTFOCUS': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                'ctl00$cboSession': self.session_name,
                'ctl00$ScriptManager1': 'ctl00$UpdatePanel1|ctl00$MainDefaultContent$gvStatus$ctl02$ctl00'
        }
        self.spost(url=BILL_TYPE_URL, data=form, allow_redirects=False)

        self.scrape_for_bill_type(BILL_LIST_URL)

    def scrape_for_bill_type(self, url):
        html = self.sget(url=url).text
        doc = lxml.html.fromstring(html)
        bills = doc.xpath('//table[@class="box_billstatusresults"]/tr')[1: ]
        for bill_info in bills:

            (bill_id, ) = bill_info.xpath('td[1]/font/input/@value')
            (sponsor, ) = bill_info.xpath('td[2]/font/input/@value')
            subject = bill_info.xpath('td[3]/font/text()')[0].strip()
            description = bill_info.xpath('td[4]/font/text()')[0].strip()
            if not description:
                description = "[No title given]"

            chamber = self.CHAMBERS[bill_id[0]]
            
            if 'B' in bill_id:
                bill_type = 'bill'
            elif 'JR' in bill_id:
                bill_type = 'joint resolution'
            elif 'R' in bill_id:
                bill_type = 'resolution'
            else:
                raise AssertionError(
                        "Unknown bill type for bill '{}'".format(bill_id))

            bill = Bill(
                    session=self.session,
                    chamber=chamber,
                    bill_id=bill_id,
                    title=description,
                    type=bill_type
                    )
            if subject:
                bill['subjects'] = [subject]
            if sponsor:
                bill.add_sponsor(type='primary', name=sponsor)
            bill.add_source(url)

            bill_url = 'http://alisondb.legislature.state.al.us/Alison/SESSBillResult.aspx?BILL={}'.format(bill_id)
            bill.add_source(bill_url)
            bill_html = self.sget(url=bill_url).text
            bill_doc = lxml.html.fromstring(bill_html)

            (viewstate, ) = bill_doc.xpath('//input[@id="__VIEWSTATE"]/@value')
            (viewstategenerator, ) = bill_doc.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
            form = {
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': viewstate,
                    '__VIEWSTATEGENERATOR': viewstategenerator,
                    'ctl00$cboSession': self.session_name,
                    }

            version_url_base = 'http://alisondb.legislature.state.al.us/ALISON/SearchableInstruments/{0}/PrintFiles/{1}-'.format(self.session, bill_id)
            versions = bill_doc.xpath('//table[@class="box_versions"]/tr/td[2]/font/text()')
            for version in versions:
                name = version
                if version == "Introduced":
                    version_url = version_url_base + 'int.pdf'
                elif version == "Engrossed":
                    version_url = version_url_base + 'eng.pdf'
                elif version == "Enrolled":
                    version_url = version_url_base + 'enr.pdf'
                else:
                    raise NotImplementedError("Unknown version type found: '{}'".format(name))

                bill.add_version(
                        name=name,
                        url=version_url,
                        mimetype='application/pdf'
                        )

            # Fiscal notes exist, but I can't figure out how to generate their URLs
            fiscal_notes = bill_doc.xpath('//table[@class="box_fiscalnote"]')[1: ]
            for fiscal_note in fiscal_notes:
                pass

            # Budget Isolation Resolutions are handled as extra actions and votes
            birs = bill_doc.xpath('//div[@class="box_bir"]//table//table/tr')[1: ]
            for bir in birs:
                bir_date = datetime.datetime.strptime(
                        bir.xpath('td[2]/font/text()')[0], self.DATE_FORMAT)
                bir_type = bir.xpath('td[1]/font/text()')[0].split(" ")[0]
                bir_chamber = self.CHAMBERS[bir_type[0]]
                bir_text = "{0}: {1}".format(
                        bir_type, bir.xpath('td[3]/font/text()')[0])

                bill.add_action(
                        actor=bir_chamber,
                        action=bir_text,
                        date=bir_date,
                        type="other"
                        )

                try:
                    (bir_vote_id, ) = bir.xpath('td[4]/font/input/@value')
                except ValueError:
                    bir_vote_id = ''

                if bir_vote_id.startswith("Roll "):
                    bir_vote_id = bir_vote_id.split(" ")[-1]

                    (eventtarget, ) = bir.xpath('td[4]/font/input/@id')
                    form['ctl00$ScriptManager1'] = 'ctl00$UpdatePanel1|' + eventtarget
                    form[eventtarget] = "Roll " + bir_vote_id
                    self.spost(url=bill_url, data=form, allow_redirects=False)

                    self.scrape_vote(
                            bill=bill,
                            vote_chamber=bir_chamber,
                            bill_id="{0}%20for%20{1}".format(bir_type, bill_id),
                            vote_id=bir_vote_id,
                            vote_date=bir_date,
                            action_text=bir_text
                            )

                    form.pop('ctl00$ScriptManager1')
                    form.pop(eventtarget)

            actions = bill_doc.xpath('//table[@class="box_history"]/tr')[1: ]
            action_date = None
            for action in actions:
                # If actions occur on the same day, only the first will list date
                if action.xpath('td[1]/font/text()')[0].strip():
                    action_date = datetime.datetime.strptime(
                            action.xpath('td[1]/font/text()')[0], self.DATE_FORMAT)

                (action_chamber, ) = action.xpath('td[2]/font/text()')
                (action_text, ) = action.xpath('td[4]/font/text()')
                action_type = _categorize_action(action_text)
                
                # The committee cell is just an abbreviation, so get its full name
                actor = self.CHAMBERS[action_chamber]
                try:
                    action_committee = re.search(
                            r'.*? referred to the (.*? committee on .*?)$',
                            action_text
                            ).group(1).strip()
                except AttributeError:
                    action_committee = ''

                bill.add_action(
                        actor=actor,
                        action=action_text,
                        date=action_date,
                        type=action_type,
                        committees=action_committee if action_committee else None
                        )

                try:
                    vote_button = action.xpath('td[9]//text()')[0].strip()
                except:
                    vote_button = None
                if vote_button:
                    vote_id = vote_button.split(" ")[-1]

                    eventtarget = action.xpath('@onclick')[0].split("'")[1]
                    eventargument = action.xpath('@onclick')[0].split("'")[3]
                    form['__EVENTTARGET'] = eventtarget
                    form['__EVENTARGUMENT'] = eventargument
                    form['ctl00$ScriptManager1'] = 'ctl00$UpdatePanel1|' + eventtarget
                    self.spost(url=bill_url, data=form, allow_redirects=False)

                    self.scrape_vote(
                            bill=bill,
                            vote_chamber=actor,
                            bill_id=bill_id,
                            vote_id=vote_id,
                            vote_date=action_date,
                            action_text=action_text
                            )

                    form.pop('ctl00$ScriptManager1')
                    form['__EVENTARGUMENT'] = ''
                    form['__EVENTTARGET'] = ''

            print(bill)
            self.save_bill(bill)

    def scrape_vote(self, bill, vote_chamber, bill_id, vote_id, vote_date, action_text):
        url = 'http://alisondb.legislature.state.al.us/Alison/GetRollCallVoteResults.aspx?VOTE={0}&BODY={1}&INST={2}&SESS={3}'.format(
                vote_id, vote_chamber, bill_id, self.session_id)
        doc = lxml.html.fromstring(self.sget(url=url).text)

        voters = {'Y': [], 'N': [], 'P': [], 'A': []}

        voters_and_votes = doc.xpath('//table/tr/td/font/text()')
        capture_vote = False
        name = ''
        for item in voters_and_votes:
            if capture_vote:
                capture_vote = False
                if name:
                    voters[item].append(name)
            else:
                capture_vote = True
                name = item
                if name.endswith(", Vacant") or not name.strip():
                    name = ''

        total_yea = len(voters['Y'])
        total_nay = len(voters['N'])
        total_other = len(voters['P']) + len(voters['A'])

        vote = Vote(vote_chamber, vote_date, action_text, total_yea > total_nay,
                    total_yea, total_nay, total_other)
        vote.add_source(url)
        for member in voters['Y']:
            vote.yes(member)
        for member in voters['N']:
            vote.no(member)
        for member in (voters['A'] + voters['P']):
            vote.other(member)

        bill.add_vote(vote)
