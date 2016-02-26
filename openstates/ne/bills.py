from datetime import datetime
import lxml.html
import urllib
from billy.scrape.bills import BillScraper, Bill
from openstates.utils import LXMLMixin


class NEBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'ne'

    def scrape(self, session, chambers):
        start_year = self.metadata['session_details'][session]['start_date'].year
        end_year = self.metadata['session_details'][session]['end_date'].year
        self.scrape_year(session, start_year)
        if start_year != end_year:
            self.scrape_year(session, end_year)

    def scrape_year(self, session, year):
        main_url = 'http://nebraskalegislature.gov/bills/search_by_date.php?'\
            'SessionDay={}'.format(year)
        page = self.lxmlize(main_url)

        document_links = self.get_nodes(
            page,
            '//div[@class="main-content"]//div[@class="panel panel-leg"]//'
            'table[@class="table table-condensed"]/tbody/tr/td[1]/a')

        for document_link in document_links:
            bill_number = document_link.text
            bill_link = document_link.attrib['href']

            #POST request for search form
            #post_dict = {'DocumentNumber': bill_number, 'Legislature': session}
            #headers = urllib.urlencode(post_dict)
            #bill_resp = self.post('http://nebraskalegislature.gov/bills/'
            #    'search_by_number.php', data=post_dict)
            #bill_link = bill_resp.url
            #bill_page = bill_resp.text

            #scrapes info from bill page
            self.bill_info(bill_link, session, main_url)

    #Scrapes info from the bill page
    def bill_info(self, bill_link, session, main_url):

        bill_page = self.lxmlize(bill_link)

        long_title = self.get_node(
            bill_page,
            '//div[@class="main-content"]/div[1]/div/h2').text.split()

        bill_number = long_title[0]
        title = ''
        for x in range(2, len(long_title)):
            title += long_title[x] + ' '
        title = title[0:-1]

        if not title:
            self.error('no title, skipping %s', bill_number)
            return

        bill_type = 'resolution' if 'LR' in bill_number else 'bill'

        bill = Bill(session, 'upper', bill_number, title, type = bill_type)

        bill.add_source(main_url)
        bill.add_source(bill_link)

        introduced_by = self.get_node(
            bill_page,
            '//div[@class="main-content"]/div[3]/div[1]/ul/li[1]/a[1]/text()')

        if not introduced_by:
            introduced_by = self.get_node(
                bill_page,
                '//div[@class="main-content"]/div[3]/div[1]/ul/li[1]/text()')
            introduced_by = introduced_by.split('Introduced By:')[1].strip()

        bill.add_sponsor('primary', introduced_by)

        action_nodes = self.get_nodes(
            bill_page,
            '//div[@class="main-content"]/div[5]//table/tbody/tr')

        for action_node in action_nodes:
            date = self.get_node(
                action_node,
                './td[1]').text
            date = datetime.strptime(date, '%b %d, %Y')

            # The action node may have an anchor element within it, so
            # we grab all the text within.
            action = self.get_node(
                action_node,
                './td[2]').text_content()

            if 'Governor' in action:
                actor = 'Governor'
            elif 'Speaker' in action:
                actor = 'Speaker'
            else:
                actor = 'upper'

            action_type = self.action_types(action)
            bill.add_action(actor, action, date, action_type)

        # Were in reverse chronological order.
        bill['actions'].reverse()

        # Grabs bill version documents.
        version_links = self.get_nodes(
            bill_page,
            '//div[@class="main-content"]/div[3]/div[2]/'
            'div[@class="hidden-xs"]/ul[1]/li/a')

        for version_link in version_links:
            version_name = version_link.text
            version_url = version_link.attrib['href']
            # replace Current w/ session number
            version_url = version_url.replace('Current', session)
            bill.add_version(version_name, version_url,
                mimetype='application/pdf')

        # Adds any documents related to amendments.
        amendment_links = self.get_nodes(
            bill_page,
            '//div[@class="main-content"]/div[5]/div[2]/table/tr/td[1]/a')

        for amendment_link in amendment_links:
            amendment_name = amendment_link.text
            amendment_url = amendment_link.attrib['href']
            bill.add_document(amendment_name, amendment_url)

        # Related transcripts.
        transcript_links = self.get_nodes(
            bill_page,
            '//div[@class="main-content"]/div[5]/div[2]/'
            'div[@class="hidden-xs"]/table/tr/td/a')

        for transcript_link in transcript_links:
            transcript_name = transcript_link.text
            transcript_url = transcript_link.attrib['href']
            bill.add_document(transcript_name, transcript_url)

        self.save_bill(bill)

    def action_types(self, action):
        if 'Date of introduction' in action:
            action_type = 'bill:introduced'
        elif 'Referred to' in action:
            action_type = 'committee:referred'
        elif 'Indefinitely postponed' in action:
            action_type = 'committee:failed'
        elif ('File' in action) or ('filed' in action):
            action_type = 'bill:filed'
        elif 'Placed on Final Reading' in action:
            action_type = 'bill:reading:3'
        elif 'Passed' in action or 'President/Speaker signed' in action:
            action_type = 'bill:passed'
        elif 'Presented to Governor' in action:
            action_type = 'governor:received'
        elif 'Approved by Governor' in action:
            action_type = 'governor:signed'
        elif 'Failed to pass notwithstanding the objections of the Governor' in action:
            action_type = 'governor:vetoed'
        elif 'Failed' in action:
            action_type = 'bill:failed'
        elif 'Bill withdrawn' in action:
            action_type = 'bill:withdrawn'
        else:
            action_type = ''
        return action_type
