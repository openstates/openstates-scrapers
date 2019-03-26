import datetime as dt
import json

from pupa.scrape import Scraper, Bill, VoteEvent
from openstates.utils import LXMLMixin
from .actions import Categorizer


class DEBillScraper(Scraper, LXMLMixin):
    categorizer = Categorizer()
    chamber_codes = {'upper': 1, 'lower': 2}
    chamber_codes_rev = {1: 'upper', 2: 'lower'}
    chamber_map = {'House': 'lower', 'Senate': 'upper'}
    legislators = {}
    legislators_by_short = {}

    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        # Cache the legislators, we'll need them for sponsors and votes
        self.scrape_legislators(session)

        # Cannot scrape a particular chamber, since the search-by-chamber
        # returns bills that are currently _active_ in a chamber,
        # and is not a search by chamber-of-origin
        per_page = 200
        page = self.post_search(session, 1, per_page)

        bills_and_votes = []
        page_number = 1
        while True:
            page = self.post_search(session, page_number, per_page)
            if not page['Data']:
                self.info("Found no more bills in pagination")
                break
            for bill in page['Data']:
                bills_and_votes.extend(list(self.scrape_bill(bill, session)))
            page_number += 1
        yield from self.filter_bills(bills_and_votes)

    def filter_bills(self, items):
        """
        Read through all bills on a page. If a bill has no subsitutes,
        yield it. If a bill does have substitutes, keep the highest-
        numbered substitute and only yield that Bill object.
        Bills may be amended (`BILL_ID w/ AMENDMENT ID` on the website),
        but if that is the case then the original (unamended) version
        should not exist any more.
        """
        # Map of {bill_id: bill}
        bills = {}

        for bill in items:
            # The generator also yields VoteEvent objects
            if isinstance(bill, VoteEvent):
                yield bill
                continue

            if bill.identifier in bills and (
                'amendment' in bill.extras or
                'amendment' in bills[bill.identifier].extras
            ) and bill.extras.get('substitute') == bills[bill.identifier].extras.get('substitute'):
                raise ValueError(
                    "Bill `{}` showed up _both_ amended and unamended"
                    .format(bill.identifier)
                )

            if bill.identifier not in bills:
                # This includes bills that were never substituted
                bills[bill.identifier] = bill
            elif 'substitute' in bill.extras and (
                'substitute' not in bills[bill.identifier].extras or
                bill.extras['substitute'] > bills[bill.identifier].extras['substitute']
            ):
                bills[bill.identifier] = bill
            else:
                self.warning("Ignoring substituted bill `{}`".format(bill.identifier))

        yield from bills.values()

    def scrape_bill(self, row, session):
        bill_id = row['LegislationDisplayCode']

        amendment = None
        substitute = None

        if bill_id.count(' ') > 1:
            if ' w/ ' in bill_id:
                self.info('Found amended bill `{}`'.format(bill_id))
                bill_id, amendment = bill_id.split(' w/ ')
            # A bill can _both_ be amended and be substituted
            if ' for ' in bill_id:
                self.info("Found substitute to use instead: `{}`".format(bill_id))
                substitute, bill_id = bill_id.split(' for ')
            if amendment is None and substitute is None:
                raise ValueError('unknown bill_id format: ' + bill_id)

        bill_type = self.classify_bill(bill_id)
        chamber = 'upper' if bill_id.startswith('S') else 'lower'

        bill = Bill(identifier=bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=row['LongTitle'],
                    classification=bill_type)
        if row['Synopsis']:
            bill.add_abstract(row['Synopsis'], 'synopsis')
        if row['ShortTitle']:
            bill.add_title(row['ShortTitle'], 'short title')
        if row['SponsorPersonId']:
            self.add_sponsor_by_legislator_id(bill, row['SponsorPersonId'], 'primary')
        if substitute:
            bill.extras['substitute'] = substitute
        if amendment:
            bill.extras['amendment'] = amendment

        # TODO: Is there a way get additional sponsors and cosponsors, and versions/fns via API?
        html_url = 'https://legis.delaware.gov/BillDetail?LegislationId={}'.format(
            row['LegislationId']
        )
        bill.add_source(html_url, note='text/html')

        html = self.lxmlize(html_url)

        additional_sponsors = html.xpath('//label[text()="Additional Sponsor(s):"]'
                                         '/following-sibling::div/a/@href')
        for sponsor_url in additional_sponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?'
                                             'personId=', '')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'primary')

        cosponsors = html.xpath('//label[text()="Co-Sponsor(s):"]/'
                                'following-sibling::div/a/@href')
        for sponsor_url in cosponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?'
                                             'personId=', '')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'cosponsor')

        versions = html.xpath('//label[text()="Original Text:"]/following-sibling::div/a/@href')
        for version_url in versions:
            media_type = self.mime_from_link(version_url)
            version_name = 'Bill Text'
            bill.add_version_link(version_name, version_url, media_type=media_type)

        fiscals = html.xpath('//div[contains(@class,"fiscalNote")]/a/@href')
        for fiscal in fiscals:
            self.scrape_fiscal_note(bill, fiscal)

        self.scrape_actions(bill, row['LegislationId'])

        if row['HasAmendments'] is True:
            self.scrape_amendments(bill, row['LegislationId'])

        yield from self.scrape_votes(bill, row['LegislationId'], session)

        yield bill

    def scrape_legislators(self, session):
        search_form_url = 'https://legis.delaware.gov/json/Search/GetFullLegislatorList'
        form = {
            'value': '',
            # note that's selectedGAs plural, it's selectedGA elsewhere
            'selectedGAs[0]': session,
            'sort': '',
            'group': '',
            'filter': '',
        }

        self.info('Fetching legislators')
        page = self.post(url=search_form_url, data=form, allow_redirects=True).json()
        assert page['Data'], "Cound not fetch legislators!"
        for row in page['Data']:
            self.legislators[str(row['PersonId'])] = row
            self.legislators_by_short[str(row['ShortName'])] = row

    def scrape_fiscal_note(self, bill, link):
        media_type = self.mime_from_link(link)
        bill.add_document_link('Fiscal Note', link, media_type=media_type)

    def scrape_votes(self, bill, legislation_id, session):
        votes_url = 'https://legis.delaware.gov/json/BillDetail/GetVotingReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        self.info('Searching for votes for {}'.format(bill.identifier))
        response = self.post(url=votes_url, data=form, allow_redirects=True)
        if response.content:
            page = json.loads(response.content.decode('utf-8'))
            if page['Total'] > 0:
                for row in page['Data']:
                    yield from self.scrape_vote(bill, row['RollCallId'], session)

    def scrape_vote(self, bill, vote_id, session):
        vote_url = 'https://legis.delaware.gov/json/RollCall/GetRollCallVoteByRollCallId'
        form = {
            'rollCallId': vote_id,
            'sort': '',
            'group': '',
            'filter': '',
        }

        self.info('Fetching vote {} for {}'.format(vote_id, bill.identifier))
        page = self.post(url=vote_url, data=form, allow_redirects=True).json()
        if page:
            roll = page['Model']
            vote_chamber = self.chamber_map[roll['ChamberName']]
            # "7/1/16 01:00 AM"
            vote_date = dt.datetime.strptime(roll['TakenAtDateTime'],
                                             '%m/%d/%y %I:%M %p').strftime('%Y-%m-%d')

            # TODO: What does this code mean?
            vote_motion = roll['RollCallVoteType']

            vote_passed = 'pass' if roll['RollCallStatus'] == 'Passed' else 'fail'
            other_count = (int(roll['NotVotingCount']) +
                           int(roll['VacantVoteCount']) +
                           int(roll['AbsentVoteCount']) +
                           int(roll['ConflictVoteCount'])
                           )
            vote = VoteEvent(chamber=vote_chamber,
                             start_date=vote_date,
                             motion_text=vote_motion,
                             result=vote_passed,
                             classification='other',
                             bill=bill,
                             legislative_session=session
                             )
            vote_pdf_url = 'https://legis.delaware.gov' \
                '/json/RollCallController/GenerateRollCallPdf' \
                '?rollCallId={}&chamberId={}'.format(vote_id, self.chamber_codes[vote_chamber])
            # Vote URL is just a generic search URL with POSTed data,
            # so provide a different link
            vote.add_source(vote_pdf_url)
            vote.pupa_id = vote_pdf_url
            vote.set_count('yes', roll['YesVoteCount'])
            vote.set_count('no', roll['NoVoteCount'])
            vote.set_count('other', other_count)

            for row in roll['AssemblyMemberVotes']:
                # AssemblyMemberId looks like it should work here,
                # but for some sessions it's bugged to only return session
                try:
                    voter = self.legislators_by_short[str(row['ShortName'])]
                    name = voter['DisplayName']
                except KeyError:
                    self.warning('could not find legislator short name %s',
                                 row['ShortName'])
                    name = row['ShortName']
                if row['SelectVoteTypeCode'] == 'Y':
                    vote.yes(name)
                elif row['SelectVoteTypeCode'] == 'N':
                    vote.no(name)
                else:
                    vote.vote('other', name)

            yield vote

    def add_sponsor_by_legislator_id(self, bill, legislator_id, sponsor_type):
        sponsor = self.legislators[str(legislator_id)]
        sponsor_name = sponsor['DisplayName']
        chamber = self.chamber_codes_rev[sponsor['ChamberId']]
        primary = sponsor_type == 'primary'
        # The multiple ways in which sponsors are collected sometimes
        # results in duplicates; prevent these
        existing_sponsor_names = [sponsor['name'] for sponsor in bill.sponsorships]
        if sponsor_name not in existing_sponsor_names:
            bill.add_sponsorship(name=sponsor_name,
                                 classification=sponsor_type,
                                 entity_type='person',
                                 chamber=chamber,
                                 primary=primary,
                                 )
        else:
            self.warning(
                "Ignoring already-known sponsor: {} for {}"
                .format(sponsor_name, bill.identifier)
            )

    def scrape_actions(self, bill, legislation_id):
        actions_url = 'https://legis.delaware.gov/json/BillDetail/GetRecentReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        self.info('Fetching actions for {}'.format(bill.identifier))
        page = self.post(url=actions_url, data=form, allow_redirects=True).json()
        for row in page['Data']:
            action_name = row['ActionDescription']
            action_date = dt.datetime.strptime(row['OccuredAtDateTime'],
                                               '%m/%d/%y').strftime('%Y-%m-%d')
            if row.get('ChamberName') is not None:
                action_chamber = self.chamber_map[row['ChamberName']]
            elif 'Senate' in row['ActionDescription']:
                action_chamber = 'upper'
            elif 'House' in row['ActionDescription']:
                action_chamber = 'lower'
            elif 'Governor' in row['ActionDescription']:
                # TODO: <obj>.bill_chamber' is not in the enumeration: [u'upper', u'lower']
                action_chamber = 'executive'
            else:
                # Actions like 'Stricken' and 'Defeated Amendemnt'
                # don't have a chamber in the data, so assume the bill's home chamber
                action_chamber = 'upper' if bill.identifier.startswith('S') else 'lower'

            categorization = self.categorizer.categorize(action_name)

            action = bill.add_action(description=action_name,
                                     date=action_date,
                                     chamber=action_chamber,
                                     classification=categorization['classification'],
                                     )

            for l in categorization['legislators']:
                action.add_related_entity(l, 'person')
            for c in categorization['committees']:
                action.add_related_entity(c, 'organization')

    def scrape_amendments(self, bill, legislation_id):
        # http://legis.delaware.gov/json/BillDetail/GetRelatedAmendmentsByLegislationId?legislationId=47185
        # http://legis.delaware.gov/json/BillDetail/GetRelatedAmendmentsByLegislationId
        amds_url = 'http://legis.delaware.gov/json/BillDetail/GetRelatedAmendmentsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        self.info('Fetching amendments for {}'.format(bill.identifier))
        # page = self.post(url=amds_url, data=form, allow_redirects=True).json()
        page = self.post(url=amds_url, data=form, allow_redirects=True).content
        if page == b'':
            return
        else:
            page = json.loads(page)

        for row in page['Data']:
            if row['PublicStatusName'] == 'Passed':
                # http://legis.delaware.gov/json/BillDetail/GeneratePdfDocument
                # ?legislationId=47252&legislationTypeId=5&docTypeId=2&legislationName=HA1
                # http://legis.delaware.gov/json/BillDetail/GenerateHtmlDocument
                # ?legislationId=47252&legislationTypeId=5&docTypeId=2&legislationName=HA1

                pdf_url = 'http://legis.delaware.gov/json/BillDetail/GeneratePdfDocument?' \
                          'legislationId={}&legislationTypeId=5&docTypeId=2'.format(
                              row['AmendmentLegislationId'])

                bill.add_version_link(
                    row['AmendmentCode'],
                    pdf_url,
                    media_type='application/pdf',
                    on_duplicate='ignore'
                )

                html_url = 'http://legis.delaware.gov/json/BillDetail/GenerateHtmlDocument?' \
                    'legislationId={}&legislationTypeId=5&docTypeId=2'.format(
                        row['AmendmentLegislationId'])

                bill.add_version_link(
                    row['AmendmentCode'],
                    html_url,
                    media_type='text/html',
                    on_duplicate='ignore'
                )

    def classify_bill(self, bill_id):
        legislation_types = (
            ('bill', 'HB'),
            ('concurrent resolution', 'HCR'),
            ('joint resolution', 'HJR'),
            ('resolution', 'HR'),
            ('bill', 'SB'),
            ('concurrent resolution', 'SCR'),
            ('joint resolution', 'SJR'),
            ('resolution', 'SR'),
        )
        for name, abbr in legislation_types:
            if abbr in bill_id:
                return name
        else:
            raise AssertionError("Could not categorize bill ID")

    def post_search(self, session, page_number, per_page):
        search_form_url = 'https://legis.delaware.gov/json/AllLegislation/GetAllLegislation'
        form = {
            'page': page_number,
            'pageSize': per_page,
            'selectedGA[0]': session,
            'coSponsorCheck': 'True',
            'selectedLegislationTypeId[0]': '1',
            'selectedLegislationTypeId[1]': '2',
            'selectedLegislationTypeId[2]': '3',
            'selectedLegislationTypeId[3]': '4',
            # Ignore the `Amendment` legislation type, `5`
            'selectedLegislationTypeId[4]': '6',
            'sort': '',
            'group': '',
            'filter': '',
            'sponsorName': '',
            'fromIntroDate': '',
            'toIntroDate': '',
        }
        page = self.post(url=search_form_url, data=form, allow_redirects=True).json()
        return page

    def mime_from_link(self, link):
        if 'HtmlDocument' in link:
            return 'text/html'
        elif 'PdfDocument' in link:
            return 'application/pdf'
        elif 'WordDocument' in link:
            return 'application/msword'
        else:
            return ''
