import datetime
import urlparse
import lxml.html

from billy.scrape.bills import BillScraper, Bill

class GABillScraper(BillScraper):
    """
        1995-2005 HTML scrapers have been written, we're not currently
        hooked up to do the old data, but the scrape1995 function
        is left intact for future use as it is clean and may prove useful
        if/when historical information is desired for Georgia.

        Starting in the 2005-2006 session a BillSummary.xml file exists
        that we use for all bill info going forward.
    """

    state = 'ga'

    _action_codes = {
        'EFF': 'other',
        'HASAS': 'other', #'House Agree Senate Amend or Sub',
        'HCA': 'other',   #'House Conference Committee Report Adopted',
        'HCAP': 'other',  #'House Conference Committee Appointed',
        'HCFR': 'committee:passed:favorable',
        'HCUF': 'committee:passed:unfavorable',
        'HDSAS': 'other', #'House Disagrees Senate Amend/Sub',
        'HDSG': 'other',
        'HFR': 'bill:reading:1',
        'HH': 'other',   # hopper
        'HI': 'other',   # insists
        'HNOM': 'other', # notice to reconsider
        'HPA': 'bill:passed',
        'HPF': 'bill:filed',
        'HPOST': 'other', # postponed
        'HRA': 'bill:passed',
        'HRAR': 'committee:referred',
        'HRECL': 'bill:failed',
        'HRECM': 'bill:withdrawn',
        'HRECO': 'other',
        'HSG': 'governor:received',
        'HSR': 'bill:reading:2',
        'HTABL': 'bill:failed',
        'HTR': 'bill:reading:3',
        'HTRL': ['bill:reading:3', 'bill:failed'],
        'HTS': 'other', # 'House Immediately Transmitted to Senate',
        'S1REF': ['bill:reading:1', 'bill:failed'],
        'S2R': 'bill:reading:2',
        'S3RLT': ['bill:reading:3', 'bill:failed'],
        'SAHAS': 'other', # 'Senate Agrees House Amend or Sub',
        'SAPPT': 'other', # 'Senate Conference Committee Appointed',
        'SCFR': 'committee:passed:favorable',
        'SCRA': 'other',  #'Senate Conference Committee Report Adopted',
        'SCUF': 'committee:passed:unfavorable',
        'SDHAS': 'other', # 'Senate Disagrees House Amend/Sub',
        'SDSG': 'other', # 'Senate Date Signed by Governor ',
        'SENG': 'other', #'Senate Engrossed',
        'SH': 'other', # hopper
        'SI': 'other', # Senate Insists
        'SNE': 'other', #'Senate Notice to Engross',
        'SNOM': 'other', #'Senate Notice to Reconsider',
        'SPA': 'bill:passed',
        'SPF': 'bill:filed',
        'SR': 'committee:referred',  # recommittal
        'SR7-1': 'other', #'Senate Rule 7-1.6(b)',
        'SRA': 'bill:passed',
        'SRAR': 'committee:referred',
        'SREC': 'other', #'Senate Recedes from amend/sub ',
        'SRECO': 'other', #'Senate Reconsidered',
        'SRI': 'bill:introduced', #'Senate Resolution Introduced',
        'SSG': 'governor:received',
        'STAB': 'other',
        'STH': 'other', # transmits to house
        'STR': 'bill:reading:3',
        'STT': 'other', #'Senate Taken from Table',
        'SW&C': 'committee:referred', # withdrawn & recommitted
        'SWREC': 'bill:withdrawn',
        'Signed Gov': 'governor:signed'
    }


    def scrape(self, chamber, session):
        # for now just go to scrape_xml, but we can add logic to decide
        self.scrape_xml(chamber, session)


    def scrape_xml(self, chamber, session):
        start_letter = 'S' if chamber == 'upper' else 'H'
        sponsor_type_dict = {'3': 'senate cosponsor',
                             '4': 'sponsor', '5': 'sponsor',}
        version_url = 'http://www1.legis.ga.gov/legis/%s/versions/' % session

        summary_url = ('http://www1.legis.ga.gov/legis/%s/list/BillSummary.xml'
                       % session)
        xml = self.urlopen(summary_url)
        doc = lxml.etree.fromstring(xml)

        for bxml in  doc.xpath('//Bill'):
            type = bxml.get('Type')

            # if this is from the other chamber skip it
            if not type.startswith(start_letter):
                continue

            bill_id = type + bxml.get('Num') + bxml.get('Suffix')
            if type in ('HB', 'SB'):
                type = 'bill'
            elif type in ('HR', 'SR'):
                type = 'resolution'
            else:
                raise ValueError('unknown type: %s' % type)

            # use short_title as title and long as description
            title = bxml.xpath('Short_Title/text()')[0]
            description = bxml.xpath('Title/text()')[0]

            bill = Bill(session, chamber, bill_id, title, type=type,
                        description=description)
            bill.add_source(summary_url)

            for sponsor in bxml.xpath('Sponsor'):
                sponsor_name, code = sponsor.text.rsplit(' ', 1)
                bill.add_sponsor(sponsor_type_dict[sponsor.get('Type')],
                                 sponsor_name, _code=code)

            for version in bxml.xpath('Versions/Version'):
                # NOTE: it is possible to get PDF versions by using .get('Id')
                # ex. URL:  legis.ga.gov/Legislation/20112012/108025.pdf
                # for now we just get HTML
                description, file_id = version.xpath('*/text()')
                bill.add_version(description, version_url + file_id)

            for action in bxml.xpath('StatusHistory/Status'):
                date = datetime.datetime.strptime(action.get('StatusDate'),
                                                  "%Y-%m-%dT%H:%M:%S")
                code = action.get('StatusCode')
                if code in ('EFF', 'Signed Gov'):
                    actor = 'executive'
                elif code[0] == 'S':
                    actor = 'upper'
                elif code[0] == 'H':
                    actor = 'lower'

                atype = self._action_codes[code]

                bill.add_action(actor, action.text, date, atype)

            self.save_bill(bill)


    # HTML scrapers for 1995-2003 probably still work, disabled for now
    def scrape1995(self, url, year, chamberName, session, number):
        "e.g. http://www.legis.ga.gov/legis/1995_96/leg/sum/sb1.htm"
        with self.lxml_context(url) as page:
            # Bill
            name = page.cssselect('h3 br')[0].tail.split('-', 1)[1].strip()
            bill = Bill(session, chamberName, number, name)

            # Versions
            bill.add_version('Current', url.replace('/sum/', '/fulltext/'))

            # Sponsorships
            rows = page.cssselect('center table tr')
            for row in rows:
                if row.text_content().strip() == 'Sponsor and CoSponsors':
                    continue
                if row.text_content().strip() == 'Links / Committees / Status':
                    break
                for a in row.cssselect('a'):
                    bill.add_sponsor('', a.text_content().strip())

            # Actions
            # The actions are in a pre table that looks like:
            """    SENATE                         HOUSE
                   -------------------------------------
                 1/13/95   Read 1st time          2/6/95
                 1/31/95   Favorably Reported
                 2/1/95    Read 2nd Time          2/7/95
                 2/3/95    Read 3rd Time
                 2/3/95    Passed/Adopted                   """

            actions = page.cssselect('pre')[0].text_content().split('\n')
            actions = actions[2:]
            for action in actions:
                senate_date = action[:22].strip()
                action_text = action[23:46].strip()
                house_date = action[46:].strip()

                if '/' not in senate_date and '/' not in house_date:
                    continue

                if senate_date:
                    bill.add_action('upper', action_text, senate_date)

                if house_date:
                    bill.add_action('lower', action_text, house_date)

            self.save_bill(bill)

    def scrape1997(self, url, year, chamberName, session, number):
        "e.g. http://www.legis.ga.gov/legis/1997_98/leg/sum/sb1.htm"
        with self.lxml_context(url) as page:
            # Grab the interesting tables on the page.
            tables = []
            for table in page.cssselect('center table'):
                if table.get('border') == '5':
                    tables.append(table)

            # Bill
            name = page.cssselect('tr > td > font > b')[0].text_content().split(
                '-', 1)[1]
            bill = Bill(session, chamberName, number, name)

            # Versions
            bill.add_version('Current', url.replace('/sum/', '/fulltext/'))

            # Sponsorships
            for a in tables[0].cssselect('a'):
                if a.text_content().strip() == 'Current':
                    break
                bill.add_sponsor('', a.text_content().strip())

            # Actions
            for row in tables[1].cssselect('tr'):
                senate_date = row[0].text_content().strip()
                action_text = row[1].text_content().strip()
                house_date = row[2].text_content().strip()
                if '/' not in senate_date and '/' not in house_date:
                    continue
                if senate_date:
                    bill.add_action('upper', action_text, senate_date)
                if house_date:
                    bill.add_action('lower', action_text, house_date)

            self.save_bill(bill)

    def scrape1999(self, url, year, chamberName, session, number):
        "e.g. http://www.legis.ga.gov/legis/1999_00/leg/sum/sb1.htm"
        with self.lxml_context(url) as lxml:
            # Grab the interesting tables on the page.
            tables = page.cssselect('table')

            # Bill
            name = tables[1].cssselect('a')[0].text_content().split('-', 1)[1]
            bill = Bill(session, chamberName, number, name)

            # Versions
            bill.add_version('Current', url.replace('/sum/', '/fulltext/'))

            # Sponsorships
            for a in tables[2].cssselect('a'):
                bill.add_sponsor('', a.text_content().strip())

            # Actions
            for row in tables[-1].cssselect('tr'):
                senate_date = row[0].text_content().strip()
                action_text = row[1].text_content().strip()
                house_date = row[2].text_content().strip()
                if '/' not in senate_date and '/' not in house_date:
                    continue
                if senate_date:
                    bill.add_action('upper', action_text, senate_date)
                if house_date:
                    bill.add_action('lower', action_text, house_date)

            self.save_bill(bill)

    def scrape2001(self, url, year, chamberName, session, number):
        "e.g. http://www.legis.ga.gov/legis/2001_02/sum/sb1.htm"
        with self.lxml_context(url) as page:
            # Grab the interesting tables on the page.
            tables = page.cssselect('table center table')

            # Bill
            name = tables[0].text_content().split('-', 1)[1]
            bill = Bill(session, chamberName, number, name)

            # Sponsorships
            for a in tables[1].cssselect('a'):
                bill.add_sponsor('', a.text_content().strip())

            # Actions
            center = page.cssselect('table center')[-1]

            for row in center.cssselect('table table')[0].cssselect('tr')[2:]:
                date = row[0].text_content().strip()
                action_text = row[1].text_content().strip()
                if '/' not in date:
                    continue
                if action_text.startswith('Senate'):
                    action_text = action_text.split(' ', 1)[1].strip()
                    bill.add_action('upper', action_text, date)
                elif action_text.startswith('House'):
                    action_text = action_text.split(' ', 1)[1].strip()
                    bill.add_action('lower', action_text, date)

            # Versions
            for row in center.cssselect('table table')[1].cssselect('a'):
                bill.add_version(a.text_content(),
                                 urlparse.urljoin(url, a.get('href')))

            self.save_bill(bill)

    def scrape2003(self, url, year, chamberName, session, number):
        "e.g. http://www.legis.ga.gov/legis/2003_04/sum/sum/sb1.htm"
        with self.lxml_context(url) as page:
            # Grab the interesting tables on the page.
            tables = page.cssselect('center table')

            # Bill
            name = tables[0].text_content().split('-', 1)[1]
            bill = Bill(session, chamberName, number, name)

            # Sponsorships
            for a in tables[1].cssselect('a'):
                bill.add_sponsor('', a.text_content().strip())

            # Actions
            center = page.cssselect('center table center')[0]

            for row in center.cssselect('table')[-2].cssselect('tr')[2:]:
                date = row[0].text_content().strip()
                action_text = row[1].text_content().strip()
                if '/' not in date:
                    continue
                if action_text.startswith('Senate'):
                    bill.add_action('upper', action_text, date)
                elif action_text.startswith('House'):
                    bill.add_action('lower', action_text, date)

            # Versions
            for row in center.cssselect('table')[-1].cssselect('a'):
                bill.add_version(a.text_content(),
                                 urlparse.urljoin(url, a.get('href')))

            self.save_bill(bill)
