from fiftystates.scrape.bills import BillScraper, Bill

import re
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
                btn_id = btn_re.search(button.text_content()).groups()[0]

                sponsor = sponsor.text_content()
                topic = topic.text_content()
                com1 = com1.text_content()
                com2 = com2.text_content()
                desc = desc.text_content()

                print bill_id, sponsor, topic, btn_id

                # get actions
                # http://alisondb.legislature.state.al.us/acas/ACTIONHistoryResultsMac.asp?OID=%s&LABEL=%s

                # fiscal notes
                #url = "http://alisondb.legislature.state.al.us/acas/ACTIONFiscalNotesResults.asp?OID=%s&LABEL=%s%s" % (oID,bill_type,bill_number)

                # sponsors
                # url = "http://alisondb.legislature.state.al.us/acas/ACTIONSponsorsResultsMac.asp?OID=%s&LABEL=%s%s" % (oID,bill_type,bill_number)


                # full text
                # http://alisondb.legislature.state.al.us/acas/searchableinstruments/2003rs/resolutions/hjr374.htm
