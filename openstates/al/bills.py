from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import re
import datetime
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

    def _refresh_session(self):
        '''
        The LIS uses ASP.NET, and this requires us to frequently
        refresh our cookie. The cookie contains a session ID, and
        this must be included in all requests in this scraper.
        '''

        url = 'http://alisondb.legislature.state.al.us/Alison/ALISONLogin.aspx?SESSIONOID={}'.format(self.session_id)
        form = {
                '__EVENTTARGET': 'ctl01$cboSession',
                # '__VIEWSTATEGENERATOR': 'BC7CB5E3',
                # '__EVENTARGUMENT': '',
                # '__LASTFOCUS': '',
                # '__VIEWSTATE': '/wEPDwUKMTY1NDU2MTA1Mg9kFgJmD2QWAgIDD2QWDgIDDxBkEBUmFFJlZ3VsYXIgU2Vzc2lvbiAyMDE1G09yZ2FuaXphdGlvbmFsIFNlc3Npb24gMjAxNRRSZWd1bGFyIFNlc3Npb24gMjAxNBRSZWd1bGFyIFNlc3Npb24gMjAxMxpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAxMhRSZWd1bGFyIFNlc3Npb24gMjAxMhRSZWd1bGFyIFNlc3Npb24gMjAxMRpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAxMBpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAwORRSZWd1bGFyIFNlc3Npb24gMjAxMBRSZWd1bGFyIFNlc3Npb24gMjAwORpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAwOBRSZWd1bGFyIFNlc3Npb24gMjAwOBpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAwNxRSZWd1bGFyIFNlc3Npb24gMjAwNxtPcmdhbml6YXRpb25hbCBTZXNzaW9uIDIwMDcUUmVndWxhciBTZXNzaW9uIDIwMDYaRmlyc3QgU3BlY2lhbCBTZXNzaW9uIDIwMDUUUmVndWxhciBTZXNzaW9uIDIwMDUaRmlyc3QgU3BlY2lhbCBTZXNzaW9uIDIwMDQUUmVndWxhciBTZXNzaW9uIDIwMDQbU2Vjb25kIFNwZWNpYWwgU2Vzc2lvbiAyMDAzGkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDAzFFJlZ3VsYXIgU2Vzc2lvbiAyMDAzG09yZ2FuaXphdGlvbmFsIFNlc3Npb24gMjAwMxRSZWd1bGFyIFNlc3Npb24gMjAwMhtGb3VydGggU3BlY2lhbCBTZXNzaW9uIDIwMDEaVGhpcmQgU3BlY2lhbCBTZXNzaW9uIDIwMDEbU2Vjb25kIFNwZWNpYWwgU2Vzc2lvbiAyMDAxGkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDAxFFJlZ3VsYXIgU2Vzc2lvbiAyMDAxFFJlZ3VsYXIgU2Vzc2lvbiAyMDAwG1NlY29uZCBTcGVjaWFsIFNlc3Npb24gMTk5ORtPcmdhbml6YXRpb25hbCBTZXNzaW9uIDIwMTEaRmlyc3QgU3BlY2lhbCBTZXNzaW9uIDE5OTkUUmVndWxhciBTZXNzaW9uIDE5OTkbT3JnYW5pemF0aW9uYWwgU2Vzc2lvbiAxOTk5FFJlZ3VsYXIgU2Vzc2lvbiAxOTk4FSYUUmVndWxhciBTZXNzaW9uIDIwMTUbT3JnYW5pemF0aW9uYWwgU2Vzc2lvbiAyMDE1FFJlZ3VsYXIgU2Vzc2lvbiAyMDE0FFJlZ3VsYXIgU2Vzc2lvbiAyMDEzGkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDEyFFJlZ3VsYXIgU2Vzc2lvbiAyMDEyFFJlZ3VsYXIgU2Vzc2lvbiAyMDExGkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDEwGkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDA5FFJlZ3VsYXIgU2Vzc2lvbiAyMDEwFFJlZ3VsYXIgU2Vzc2lvbiAyMDA5GkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDA4FFJlZ3VsYXIgU2Vzc2lvbiAyMDA4GkZpcnN0IFNwZWNpYWwgU2Vzc2lvbiAyMDA3FFJlZ3VsYXIgU2Vzc2lvbiAyMDA3G09yZ2FuaXphdGlvbmFsIFNlc3Npb24gMjAwNxRSZWd1bGFyIFNlc3Npb24gMjAwNhpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAwNRRSZWd1bGFyIFNlc3Npb24gMjAwNRpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMjAwNBRSZWd1bGFyIFNlc3Npb24gMjAwNBtTZWNvbmQgU3BlY2lhbCBTZXNzaW9uIDIwMDMaRmlyc3QgU3BlY2lhbCBTZXNzaW9uIDIwMDMUUmVndWxhciBTZXNzaW9uIDIwMDMbT3JnYW5pemF0aW9uYWwgU2Vzc2lvbiAyMDAzFFJlZ3VsYXIgU2Vzc2lvbiAyMDAyG0ZvdXJ0aCBTcGVjaWFsIFNlc3Npb24gMjAwMRpUaGlyZCBTcGVjaWFsIFNlc3Npb24gMjAwMRtTZWNvbmQgU3BlY2lhbCBTZXNzaW9uIDIwMDEaRmlyc3QgU3BlY2lhbCBTZXNzaW9uIDIwMDEUUmVndWxhciBTZXNzaW9uIDIwMDEUUmVndWxhciBTZXNzaW9uIDIwMDAbU2Vjb25kIFNwZWNpYWwgU2Vzc2lvbiAxOTk5G09yZ2FuaXphdGlvbmFsIFNlc3Npb24gMjAxMRpGaXJzdCBTcGVjaWFsIFNlc3Npb24gMTk5ORRSZWd1bGFyIFNlc3Npb24gMTk5ORtPcmdhbml6YXRpb25hbCBTZXNzaW9uIDE5OTkUUmVndWxhciBTZXNzaW9uIDE5OTgUKwMmZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2cWAWZkAgUPDxYCHgRUZXh0BTJIb3VzZSBDb252ZW5lOiZuYnNwOyAmbmJzcDswMy8wMy8yMDE1ICAgMTI6MDAgTm9vbmRkAgcPDxYCHwAFHVNlbmF0ZSBDb252ZW5lOiAwMy8wMy8yMDE1ICAgZGQCCQ8PFgIfAGVkZAILDw8WAh8AZWRkAg8PDxYCHwBlZGQCEQ88KwANAQAPFgIeCEl0ZW1XcmFwaGRkGAIFHl9fQ29udHJvbHNSZXF1aXJlUG9zdEJhY2tLZXlfXxYDBRJjdGwwMCRpbWdUeHRTZWFyY2gFF2N0bDAwJGltZ0ZpbmRMZWdpc2xhdG9yBRNjdGwwMCRpbWdJbnN0cnVtZW50BQ1jdGwwMCRUb3BNZW51Dw9kBRNTZXNzaW9uIEluZm9ybWF0aW9uZOOaG9EGekZlaxN8IIfx9JZl7aZamKEveTZcLCEm1Zl1',
                # 'ctl01$cboSession': 'First Special Session 2009'
                'ctl01$cboSession': self.metadata['session_details'][self.session]['display_name']
                }
        self.post(url, data=form)
        # print(self.cookies)

    def scrape(self, session, chambers):
        self.session = session
        self.session_id = self.metadata['session_details'][session]['internal_id']
        self.base_doc_url = 'http://alisondb.legislature.state.al.us/ALISON/SearchableInstruments/%s/PrintFiles/' % session

        res_url = 'http://alisondb.legislature.state.al.us/Alison/SESSResList.aspx?STATUSCODES=Had%20First%20Reading%20House%20of%20Origin&BODY=999999'
        self.scrape_for_bill_type(session, res_url)

        bill_url = 'http://alisondb.legislature.state.al.us/Alison/SESSBillsList.aspx?STATUSCODES=Had%20First%20Reading%20House%20of%20Origin&BODY=999999'
        self.scrape_for_bill_type(session, bill_url)

    def scrape_for_bill_type(self, session, url):
        self._refresh_session()

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        bills = doc.xpath('//table[@class="box_billstatusresults"]/tr')
        for bill_info in bills:
            self._refresh_session()

            (bill_id, ) = bill_info.xpath(
                    'td[@class="CellSpace_bill"]/input/@value')
            (sponsor_name, ) = bill_info.xpath(
                    'td[@class="CellSpace"]/input/@value')
            subject = bill_info.xpath('td[3]/text()')[0].strip()
            description = bill_info.xpath('td[4]/text()')[0].strip()

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
                    session=session,
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
            bill_html = self.get(bill_url).text
            bill_doc = lxml.html.fromstring(bill_html)

            version_url_base = 'http://alisondb.legislature.state.al.us/ALISON/SearchableInstruments/{0}/PrintFiles/{1}-'.format(session, bill_id)
            versions = bill_doc.xpath('//table[@class="box_versions"]/tr/td[2]/text()')
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
                        bir.xpath('td[2]/text()')[0], DATE_FORMAT)
                bir_type = bir.xpath('td[2]/text()')[0].split(" ")[0]
                bir_chamber = self.CHAMBERS[bir_type[0]]
                bir_text = "{0}: {1}".format(
                        bir_type, bir.xpath('td[3]/text()')[0])

                (bir_vote_id, ) = bir.xpath('td[4]/input/@value')
                if bir_vote_id.startswith("Roll "):
                    bir_vote_id = bir_vote_id.split(" ")[-1]
                    self.scrape_vote(
                            bill=bill,
                            vote_chamber=bir_chamber,
                            bill_id="{0}%20for%20{1}".format(bir_type, bill_id),
                            vote_id=bir_vote_id,
                            vote_date=bir_date,
                            action_text=bir_text
                            )

            action_header = actions = bill_doc.xpath('//table[@class="box_history"]/tr[1]/text()')
            assert action_header == ["Calendar Date", "Body", "Amd/Sub", "Matter", "Committee", "Nay", "Yea", "Abstain", "Vote"]
            actions = bill_doc.xpath('//table[@class="box_history"]/tr')[1: ]
            action_date = None
            for action in actions:

                # If actions occur on the same day, only the first will list date
                if action.xpath('td[1]/text()')[0].strip():
                    action_date = datetime.datetime.strptime(
                            action.xpath('td[1]/text()')[0], DATE_FORMAT)

                (action_chamber, ) = action.xpath('td[2]/text()')
                (action_committee, ) = action.xpath('td[5]/text()')
                if action_committee.strip():
                    # The committee cell is just an abbreviation, so get its full name
                    action_committee = re.search(
                            r'.*? referred to the (.*? committee on .*?)$').group(1)
                    actor = action_committee
                else:
                    actor = self.CHAMBERS[action_chamber]

                (action_text, ) = action.xpath('td[4]/text()')
                action_type = self._categorize_action(action_text)

                bill.add_action(
                        actor=actor,
                        action=action_text,
                        date=action_date,
                        type=action_type,
                        committees=action_committee if action_committee.strip() else None
                        )

                vote_button = action.xpath('td[9]/text()')[0].strip()
                if vote_button:
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

    def scrape_vote(self, bill, vote_chamber, bill_id, vote_id, action_date, action_text):
        url = 'http://alisondb.legislature.state.al.us/Alison/GetRollCallVoteResults.aspx?VOTE={0}&BODY={1}&INST={2}&SESS={3}'.format(
                vote_id, vote_chamber, bill_id, self.session_id)
        doc = lxml.html.fromstring(self.get(url).text)

        voters = {'Y': [], 'N': [], 'P': [], 'A': []}

        voters_and_votes = doc.xpath('//table/tr/td/text()')
        capture_vote = False
        name = None
        for item in voters_and_votes:
            if capture_vote:
                capture_vote = False
                if name:
                    voters[item].append(name)
            else:
                capture_vote = True
                if name.endswith(", Vacant"):
                    name = None
                else:
                    name = item

        total_yea = len(voters['Y'])
        total_nay = len(voters['N'])
        total_other = len(voters['P']) + len(voters['A'])

        vote = Vote(vote_chamber, action_date, action_text, total_yea > total_nay,
                    total_yea, total_nay, total_other)
        vote.add_source(url)
        for member in voters['Y']:
            vote.yes(member)
        for member in voters['N']:
            vote.no(member)
        for member in (voters['A'] + voters['P']):
            vote.other(member)

        bill.add_vote(vote)
