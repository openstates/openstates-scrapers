import lxml.html

from fiftystates.scrape.bills import BillScraper, Bill


class DCBillScraper(BillScraper):
    state = 'dc'

    def scrape_bill(self, bill):
        bill_url = 'http://www.dccouncil.washington.dc.us/lims/legislation.aspx?LegNo=' + bill['bill_id']

        bill.add_source(bill_url)

        with self.urlopen(bill_url) as bill_html:
            doc = lxml.html.fromstring(bill_html)
            doc.make_links_absolute(bill_url)

            # get versions
            for link in doc.xpath('//a[starts-with(@id, "DocumentRepeater")]'):
                bill.add_version(link.text, link.get('href'))

            # sponsors
            introduced_by = doc.get_element_by_id('IntroducedBy').text
            requested_by = doc.get_element_by_id('RequestedBy').text
            cosponsored_by = doc.get_element_by_id('CoSponsoredBy').text
            bill.add_sponsor('primary', introduced_by)
            if requested_by:
                bill.add_sponsor('requestor', requested_by)
            for cosponsor in cosponsored_by.split(','):
                bill.add_sponsor('cosponsor', cosponsor)

            actions = {
                'Introduction': 'DateIntroduction',
                'Committee Action': 'DateCommitteeAction',
                'Report Filed': 'ReportFiled',
                'COW Action': 'COWAction',
                'First Vote': 'DateFirstVote',
                'Final Vote': 'DateFinalVote',
                'Third Vote': 'DateThirdVote',
                'Reconsideration': 'DateReconsideration',
                'Transmitted to Mayor': 'DateTransmittedMayor',
                'Signed by Mayor': 'DateSigned',
                'Returned by Mayor': 'DateReturned',
                'Veto Override': 'DateOverride',
                'Enacted': 'DateEnactment',
                'Vetoed by Mayor': 'DateVeto',
                'Transmitted to Congress': 'DateTransmittedCongress',
                'Re-transmitted to Congress': 'DateReTransmitted',
            }

            # actions
            for action, elem_id in actions.iteritems():
                date = doc.get_element_by_id(elem_id).text
                if date:
                    actor = 'mayor' if action.endswith('by Mayor') else 'upper'
                    # TODO: convert dates
                    bill.add_action(actor, action, date)

        return bill


    def scrape(self, chamber, session):
        self.validate_session(session)

        # no lower chamber
        if chamber == 'lower':
            return

        url = 'http://www.dccouncil.washington.dc.us/lims/print/list.aspx?FullPage=True&Period=' + session

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            rows = doc.xpath('//table/tr')
            # skip first row
            for row in rows[1:]:
                bill_id, title, _ = row.xpath('td/text()')
                bill = Bill(session, 'upper', bill_id, title)
                self.scrape_bill(bill)
