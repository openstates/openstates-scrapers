import datetime
import re

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import lxml.html
import scrapelib


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
    ('Passed by House of Origin', 'bill:passed'),
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

    # Tweak which responses are acceptible to the scrapelib internals
    def accept_response(self, response, **kwargs):
        # Errored requests should be retried
        if response.status_code >= 400:
            return False

        # Almost all GET requests should _not_ get redirected
        elif (response.status_code == 302 and
              response.request.method == 'GET' and
              'ALISONLogin.aspx' not in response.request.url):
            return False

        # Standard GET responses must have an ASP.NET VIEWSTATE
        # If they don't, it means the page is a trivial error message
        elif (not lxml.html.fromstring(response.text).xpath(
                  '//input[@id="__VIEWSTATE"]/@value') and
              response.request.method == 'GET'):
            return False

        else:
            return True

    def _set_session(self, session):
        ''' Activate an ASP.NET session, and set the legislative session '''

        SESSION_SET_URL = ('http://alisondb.legislature.state.al.us/'
                           'Alison/SelectSession.aspx')

        doc = lxml.html.fromstring(self.get(url=SESSION_SET_URL).text)
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath(
            '//input[@id="__VIEWSTATEGENERATOR"]/@value')

        # Find the link whose text matches the session metadata _scraped_name on the session list page
        # The __EVENTARGUMENT form value we need to set the session is the second argument
        # to the __doPostBack JS function, which is the href of each that link 
        (target_session, ) = doc.xpath('//table[@id="ContentPlaceHolder1_gvSessions"]//tr//a/font'
                                        '[text()="{}"]/parent::a/@href'.format(self.session_name))
        target_session = target_session.replace("javascript:__doPostBack('ctl00$ContentPlaceHolder1$gvSessions','",'')
        target_session = target_session.replace("')",'')

        form = {
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$gvSessions',
            '__EVENTARGUMENT': target_session,
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            
        }
        self.post(url=SESSION_SET_URL, data=form, allow_redirects=True)

    def _get_bill_list(self, url):
        '''
        For the bill list and resolution list, require that at least
        one piece of legislation has been found
        '''

        for _retry in range(self.retry_attempts):
            html = self.get(url=url).text

            doc = lxml.html.fromstring(html)

            listing = doc.xpath('//table[@id="ContentPlaceHolder1_gvBills"]/tr')[1:]

            if listing:
                return listing
            elif doc.xpath(
                    '//span[@id="ContentPlaceHolder1_lblCount"]/font/text()'
                    ) == ["0 Instruments", ]:
                self.warning("Missing either bills or resolutions")
                return []
            else:
                print "Attempt"
                print doc.xpath(
                    '//span[@id="ContentPlaceHolder1_lblCount"]/text()'
                    )
                continue
        else:
            raise AssertionError("Bill list not found")

    def _get_bill_response(self, url):
        ''' Ensure that bill pages loaded fully '''

        try:
            html = self.get(url=url, allow_redirects=False).text
            if lxml.html.fromstring(html).xpath(
                    '//span[@id="ContentPlaceHolder1_lblShotTitle"]'):
                return html
        # If a bill page doesn't exist yet, ignore redirects and timeouts
        except scrapelib.HTTPError:
            pass
        return None

    def scrape(self, session, chambers):
        self.validate_session(session)

        self.session = session
        self.session_name = (self.metadata['session_details']
                             [self.session]['_scraped_name'])
        self.session_id = (self.metadata['session_details']
                           [self.session]['internal_id'])

        self._set_session(session)

        # Acquire and process a list of all bills
        BILL_TYPE_URL = ('http://alisondb.legislature.state.al.us/Alison/'
                         'SESSBillsBySelectedStatus.aspx')
        BILL_LIST_URL = ('http://alisondb.legislature.state.al.us/Alison/'
                         'SESSBillsList.aspx?STATUSCODES=Had%20First%20Reading'
                         '%20House%20of%20Origin&BODY=999999')

        doc = lxml.html.fromstring(self.get(url=BILL_TYPE_URL).text)
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath(
            '//input[@id="__VIEWSTATEGENERATOR"]/@value')
        form = {
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$gvStatus$ctl02$ctl00',
            '__EVENTARGUMENT': 'Select$0',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            'ctl00$ScriptManager1': 'ctl00$UpdatePanel1|ctl00$'
                                    'MainDefaultContent$gvStatus$ctl02$ctl00'
        }
        self.post(url=BILL_TYPE_URL, data=form, allow_redirects=True)

        self.scrape_bill_list(BILL_LIST_URL)

        self._set_session(session)

        # Acquire and process a list of all resolutions
        RESOLUTION_TYPE_URL = (
            'http://alisondb.legislature.state.al.us/Alison/'
            'SESSResosBySelectedStatus.aspx?BODYID=1755')
        RESOLUTION_LIST_URL = (
            'http://alisondb.legislature.state.al.us/Alison/'
            'SESSResosList.aspx?STATUSCODES=Had%20First%20Reading'
            '%20House%20of%20Origin&BODY=999999')

        resText = self.get(url=RESOLUTION_TYPE_URL).text

        doc = lxml.html.fromstring(resText)
        
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath(
            '//input[@id="__VIEWSTATEGENERATOR"]/@value')

        form = {
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$gvStatus$ctl02$ctl00',
            '__EVENTARGUMENT': 'Select$0',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            'ctl00$ScriptManager1': 'tctl00$UpdatePanel1|ctl00$'
                                    'MainDefaultContent$gvStatus$ctl02$ctl00'
        }
        
        deb = self.post(url=RESOLUTION_TYPE_URL, data=form, allow_redirects=True)
        
        self.scrape_bill_list(RESOLUTION_LIST_URL)

    def scrape_bill_list(self, url):
        bill_list = self._get_bill_list(url)
        
        for bill_info in bill_list:
            
            (bill_id, ) = bill_info.xpath('td[1]/font/input/@value')
            (sponsor, ) = bill_info.xpath('td[2]/font/input/@value')
            (subject, ) = bill_info.xpath('td[3]//text()')
            subject = subject.strip()
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
                title='',
                type=bill_type
            )
            if subject:
                bill['subjects'] = [subject]
            if sponsor:
                bill.add_sponsor(type='primary', name=sponsor)
            bill.add_source(url)

            bill_url = ('http://alisondb.legislature.state.al.us/Alison/'
                        'SESSBillStatusResult.aspx?BILL={}'.format(bill_id))
            bill.add_source(bill_url)

            bill_html = self._get_bill_response(bill_url)
            if bill_html is None:
                self.warning("Bill {} has no webpage, and will be skipped".
                             format(bill_id))
                continue
            bill_doc = lxml.html.fromstring(bill_html)

            if( bill_doc.xpath(
                '//span[@id="ContentPlaceHolder1_lblShotTitle"]') ):
                title = bill_doc.xpath(
                '//span[@id="ContentPlaceHolder1_lblShotTitle"]')[0].text_content().strip()
            if not title:
                title = "[No title given by state]"
            bill['title'] = title

            # Code to fix the session in the case of Special Sessions, which breaks version_url_base
            version_url_session = self.session
            first_session_string = "First Special Session"
            if version_url_session[:len(first_session_string)] == first_session_string:
                version_url_session = version_url_session[len(first_session_string)+1:] + "FS"
            second_session_string = "Second Special Session"
            if version_url_session[:len(second_session_string)] == second_session_string:
                version_url_session = version_url_session[len(second_session_string)+1:] + "SS"

            version_url_base = (
                'http://alisondb.legislature.state.al.us/ALISON/'
                'SearchableInstruments/{0}/PrintFiles/{1}-'.
                format(version_url_session, bill_id))
            versions = bill_doc.xpath(
                '//table[@class="box_versions"]/tr/td[2]/font/text()')
            for version in versions:
                name = version
                if version == "Introduced":
                    version_url = version_url_base + 'int.pdf'
                elif version == "Engrossed":
                    version_url = version_url_base + 'eng.pdf'
                elif version == "Enrolled":
                    version_url = version_url_base + 'enr.pdf'
                else:
                    raise NotImplementedError(
                        "Unknown version type found: '{}'".format(name))

                bill.add_version(
                    name=name,
                    url=version_url,
                    mimetype='application/pdf'
                )

            # Fiscal notes exist, but I can't figure out how to build their URL
            fiscal_notes = bill_doc.xpath(
                '//table[@class="box_fiscalnote"]')[1:]
            for fiscal_note in fiscal_notes:
                pass

            # Budget Isolation Resolutions are handled as extra actions/votes
            birs = bill_doc.xpath(
                '//div[@class="box_bir"]//table//table/tr')[1:]
            for bir in birs:
                bir_action = bir.xpath('td[1]')[0].text_content().strip()
                # Sometimes ALISON's database puts another bill's
                # actions into the BIR action list; ignore these
                if bill_id not in bir_action:
                    self.warning(
                        "BIR action found ({}) ".format(bir_action) +
                        "that doesn't match the bill ID ({})".format(bill_id))
                    continue

                bir_date = datetime.datetime.strptime(
                    bir.xpath('td[2]/font/text()')[0], self.DATE_FORMAT)
                bir_type = bir.xpath('td[1]/font/text()')[0].split(" ")[0]
                bir_chamber = self.CHAMBERS[bir_type[0]]
                bir_text = "{0}: {1}".format(
                    bir_type, bir.xpath('td[3]/font/text()')[0].strip())

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

                bir_vote_id = bir_vote_id.strip()
                if bir_vote_id.startswith("Roll "):
                    bir_vote_id = bir_vote_id.split(" ")[-1]

                    self.scrape_vote(
                        bill=bill,
                        vote_chamber=bir_type[0],
                        bill_id="{0}%20for%20{1}".format(bir_type, bill_id),
                        vote_id=bir_vote_id,
                        vote_date=bir_date,
                        action_text=bir_text
                    )

            actions = bill_doc.xpath('//table[@id="ContentPlaceHolder1_gvHistory"]/tr')[1:]
            action_date = None
            for action in actions:
                # If actions occur on the same day, only one date will exist
                if (action.xpath('td[1]/font/text()')[0].
                        encode('ascii', 'ignore').strip()):
                    action_date = datetime.datetime.strptime(
                        action.xpath('td[1]/font/text()')[0], self.DATE_FORMAT)

                (action_chamber, ) = action.xpath('td[2]/font/text()')
                (action_text, ) = action.xpath('td[4]/font/text()')
                action_type = _categorize_action(action_text)

                # check for occasional extra last row
                if not action_chamber.strip():
                    continue

                # The committee cell is just an abbreviation, so get its name
                actor = self.CHAMBERS[action_chamber]
                try:
                    action_committee = re.search(
                        r'.*? referred to the .*? committee on (.*?)$',
                        action_text).group(1).strip()
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
                    vote_button = ''
                if vote_button.startswith("Roll "):
                    vote_id = vote_button.split(" ")[-1]

                    self.scrape_vote(
                        bill=bill,
                        vote_chamber=action_chamber,
                        bill_id=bill_id,
                        vote_id=vote_id,
                        vote_date=action_date,
                        action_text=action_text
                    )

            self.save_bill(bill)

    def scrape_vote(self, bill, vote_chamber, bill_id, vote_id, vote_date,
                    action_text):
        url = ('http://alisondb.legislature.state.al.us/Alison/'
               'GetRollCallVoteResults.aspx?'
               'VOTE={0}&BODY={1}&INST={2}&SESS={3}'.
               format(vote_id, vote_chamber, bill_id, self.session_id))
        doc = lxml.html.fromstring(self.get(url=url).text)

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
                if (name.endswith(", Vacant") or
                        name.startswith("Total ") or
                        not name.strip()):
                    name = ''

        # Check name counts against totals listed on the site
        total_yea = doc.xpath('//*[starts-with(text(), "Total Yea")]/text()')
        if total_yea:
            total_yea = int(total_yea[0].split(":")[-1])
            assert total_yea == len(voters['Y']), "Yea count incorrect"
        else:
            total_yea = len(voters['Y'])

        total_nay = doc.xpath('//*[starts-with(text(), "Total Nay")]/text()')
        if total_nay:
            total_nay = int(total_nay[0].split(":")[-1])
            assert total_nay == len(voters['N']), "Nay count incorrect"
        else:
            total_nay = len(voters['N'])

        total_absent = doc.xpath(
            '//*[starts-with(text(), "Total Absent")]/text()')
        if total_absent:
            total_absent = int(total_absent[0].split(":")[-1])
            assert total_absent == len(voters['A']), "Absent count incorrect"
        total_other = len(voters['P']) + len(voters['A'])

        vote = Vote(
            self.CHAMBERS[vote_chamber[0]], vote_date, action_text,
            total_yea > total_nay, total_yea, total_nay, total_other)
        vote.add_source(url)
        for member in voters['Y']:
            vote.yes(member)
        for member in voters['N']:
            vote.no(member)
        for member in (voters['A'] + voters['P']):
            vote.other(member)

        bill.add_vote(vote)
