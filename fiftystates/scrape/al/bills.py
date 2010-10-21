from fiftystates.scrape.bills import BillScraper, Bill

import re
import datetime
import lxml.html

bill_id_re = re.compile('(H|S)B\d+')
btn_re = re.compile('BTN(\d+)')

class ALBillScraper(BillScraper):

    state = 'al'

    def refresh_session(self):
        url = 'http://alisondb.legislature.state.al.us/acas/ACASLogin.asp?SESSION=%s' % self.site_id
        self.urlopen(url)

    def scrape(self, chamber, session):
        self.site_id = self.metadata['session_details'][session]['internal_id']
        chamber_piece = {'upper': 'Senate',
                         'lower': 'House+of+Representatives'}[chamber]

        # resolutions
        # http://alisondb.legislature.state.al.us/acas/SESSResosBySelectedMatterTransResults.asp?WhichResos=Senate&TransCodes={All}&LegDay={All}%22&GetBillsTrans=Get+Resolutions+by+Transaction

        url = 'http://alisondb.legislature.state.al.us/acas/SESSBillsBySelectedMatterTransResults.asp?TransCodes={All}&LegDay={All}&WhichBills=%s' % chamber_piece

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
                _, button, sponsor, topic, _, _, com1, com2, _ = details.xpath('td')

                # pull bill_id out of script tag (gross)
                bill_id = bill_id_re.search(button.text_content()).group()
                oid = btn_re.search(button.text_content()).groups()[0]

                sponsor = sponsor.text_content()
                topic = topic.text_content()
                com1 = com1.text_content()
                com2 = com2.text_content()
                desc = desc.text_content()

                # create bill
                bill = Bill(session, chamber, bill_id, desc, topic=topic)
                bill.add_sponsor(sponsor, 'primary')

                self.get_sponsors(bill, oid)
                self.get_actions(bill, oid)

                # craft bill URL
                session_fragment = '2010rs'
                type_fragment = 'bills'
                bill_id_fragment = bill_id.lower()
                bill_text_url = 'http://alisondb.legislature.state.al.us/acas/searchableinstruments/%s/%s/%s.htm' % (
                    session_fragment, type_fragment, bill_id_fragment)
                bill.add_version('bill text', bill_text_url)

                self.save_bill(bill)


    def get_actions(self, bill, oid):
        url = 'http://alisondb.legislature.state.al.us/acas/ACTIONHistoryResultsMac.asp?OID=%s&LABEL=%s' % (oid, bill['bill_id'])

        bill.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for row in doc.xpath('//tr[@valign="top"]'):
                tds = row.xpath('td')
                # date, amend/subst, matter, committee, nay, yea, abs, vote

                # TODO: action parsing could be greatly improved
                #   - it is unclear what it means when date is missing
                #   - nothing done with amend/subst
                #   - votes not handled yet
                #   - actor isn't provided.. unclear what can be done

                # only change date if it exists (actions w/o date get old date)
                if tds[0].text_content():
                    date = datetime.datetime.strptime(tds[0].text_content(),
                                                      '%m/%d/%Y')

                bill.add_action(bill['chamber'], tds[2].text_content(), date)

    def get_sponsors(self, bill, oid):
        url = "http://alisondb.legislature.state.al.us/acas/ACTIONSponsorsResultsMac.asp?OID=%s&LABEL=%s" % (oid, bill['bill_id'])

        bill.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            # cosponsors in really weird table layout (likely to break)
            for cs in doc.xpath('//table[2]/tr/td[2]/table/tr/td/text()'):
                bill.add_sponsor(cs, 'cosponsor')


    #def getvote(moid, bill_type, bill_number, voteid, bodyoid, sessionid):
    #    url = "http://alisondb.legislature.state.al.us/acas/GetRollCallVoteResults.asp?MOID=%s&VOTE=%s&BODY=%s&INST=%s%s&SESS=%s" % (moid,voteid,bodyoid,bill_type,bill_number,sessionid)
