import datetime as dt
import json
import math

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
    chamber_name = ''

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        # Cache the legislators, we'll need them for sponsors and votes
        self.scrape_legislators(session)

        chambers = [chamber] if chamber else ['upper', 'lower']

        for chamber in chambers:
            # cache the camber name.
            self.chamber_name = chamber
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        per_page = 50
        page = self.post_search(session, chamber, 1, per_page)

        for row in page['Data']:
            yield from self.filter_substitutes(self.scrape_bill(row, chamber, session))

        max_results = int(page["Total"])
        if max_results > per_page:
            max_page = int(math.ceil(max_results / per_page))

            for i in range(2, max_page):
                page = self.post_search(session, chamber, i, per_page)
                for row in page['Data']:
                    yield from self.filter_substitutes(self.scrape_bill(row, chamber, session))

    def filter_substitutes(self, bills):
        """
        called as a pass through around scrape_bill
        if a bill is a substitute, holds it until the end of the stream
        ensuring that there aren't multiple substitutes for a given bill
        in the final stream
        """
        # bill_id: bill
        substitutes = {}

        # iterate over all bills in parent generator
        for bill in bills:
            if 'substitute' in bill.extras:
                # if we haven't seen this bill_id or the sub# > stored sub#
                if (bill.identifier not in substitutes or
                        bill.extras['substitute'] >
                        substitutes[bill.identifier].extras['substitute']):
                    substitutes[bill.identifier] = bill
            else:
                # pass through if not sub
                yield bill

        # yield final subs
        yield from substitutes.values()

    def scrape_bill(self, row, chamber, session):
        bill_id = row['LegislationDisplayCode']

        # hack for empty StatusName
        statusless_bills = ['HA 2 to SS 1 for SB 5', 'HA 3 to SS 1 for SB 5']
        is_force_substitute = bill_id in statusless_bills \
            and row['StatusName'] is None

        is_substituted = is_force_substitute or 'Substituted' in row['StatusName'] \

        if is_substituted:
            # skip substituted bills, the replacement is picked up instead
            self.warning('skipping %s: %s', bill_id, row['StatusName'])
            return

        substitute = None

        if bill_id.count(' ') > 1:
            if 'w/' in bill_id or 'SA' in bill_id or 'HA' in bill_id:
                # TODO: re-evaluate if these should be separate bills
                self.warning('skipping amendment %s', bill_id)
                return
            elif 'for' in bill_id:
                print(bill_id)
                substitute, bill_id = bill_id.split(' for ')
            else:
                raise ValueError('unknown bill_id format: ' + bill_id)

        bill_type = self.classify_bill(bill_id)

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

        # TODO: Is there a way get additional sponsors and cosponsors, and versions/fns via API?
        html_url = 'https://legis.delaware.gov/BillDetail?LegislationId={}'.format(
            row['LegislationId']
        )
        bill.add_source(html_url, note='text/html')

        html = self.lxmlize(html_url)

        # Additional Sponsors: '//label[text()="Additional Sponsor(s):"]/following-sibling::div/a'
        additional_sponsors = html.xpath('//label[text()="Additional Sponsor(s):"]'
                                         '/following-sibling::div/a/@href')
        for sponsor_url in additional_sponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?'
                                             'personId=', '')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'primary')

        # CoSponsors: '//label[text()="Co-Sponsor(s):"]/following-sibling::div/a'
        cosponsors = html.xpath('//label[text()="Additional Sponsor(s):"]/'
                                'following-sibling::div/a/@href')
        for sponsor_url in cosponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?'
                                             'personId=', '')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'cosponsor')

        versions = html.xpath('//label[text()="Original Text:"]/following-sibling::div/a/@href')
        for version_url in versions:
            media_type = self.mime_from_link(version_url)
            version_name = 'Bill Text'
            # on_duplicate='error'
            bill.add_version_link(version_name, version_url, media_type=media_type)

        fiscals = html.xpath('//div[contains(@class,"fiscalNote")]/a/@href')
        for fiscal in fiscals:
            self.scrape_fiscal_note(bill, fiscal)

        self.scrape_actions(bill, row['LegislationId'])
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

        # response = self.post(url=search_form_url, data=form, allow_redirects=True)
        page = self.post(url=search_form_url, data=form, allow_redirects=True).json()
        if int(page['Total']) > 0:
            for row in page['Data']:
                self.legislators[str(row['PersonId'])] = row
                self.legislators_by_short[str(row['ShortName'])] = row
        else:
            self.warning("Error returning legislator list!")

    def scrape_fiscal_note(self, bill, link):
        # https://legis.delaware.gov/json/BillDetail/GetHtmlDocument?fileAttachmentId=48095
        # The DE site for some reason POSTS to an endpoint for fiscal notes
        # then pops the JSON response into a new window.
        # But the attachment endpoint for bill versions works fine.
        attachment_id = link.replace('GetFiscalNoteHtmlDocument(event, ', '').replace(')', '')
        fn_url = 'https://legis.delaware.gov/json/BillDetail/'
        'GetHtmlDocument?fileAttachmentId={}'.format(attachment_id)
        # on_duplicate='error'
        bill.add_document_link('Fiscal Note', fn_url, media_type='text/html')

    def scrape_votes(self, bill, legislation_id, session):
        votes_url = 'https://legis.delaware.gov/json/BillDetail/GetVotingReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        response = self.post(url=votes_url, data=form, allow_redirects=True)
        if response.content:
            page = json.loads(response.content.decode('utf-8'))
            # page = self.post(url=votes_url, data=form, allow_redirects=True).json()
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
            vote.add_source(vote_url)
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

            # bill.add_vote_event(vote)
            yield vote

    def add_sponsor_by_legislator_id(self, bill, legislator_id, sponsor_type):
        sponsor = self.legislators[str(legislator_id)]
        sponsor_name = sponsor['DisplayName']
        chamber = self.chamber_codes_rev[sponsor['ChamberId']]
        bill.add_sponsorship(name=sponsor_name,
                             classification=sponsor_type,
                             entity_type='person',
                             chamber=chamber,
                             primary=sponsor_type == 'primary',
                             )

    def scrape_actions(self, bill, legislation_id):
        actions_url = 'https://legis.delaware.gov/json/BillDetail/GetRecentReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
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
                if self.chamber_name == 'lower':
                    action_chamber = 'lower'
                else:
                    action_chamber = 'upper'

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

        return ''

    def post_search(self, session, chamber, page_number, per_page):
        search_form_url = 'https://legis.delaware.gov/json/AllLegislation/GetAllLegislation'
        form = {
            'page': page_number,
            'pageSize': per_page,
            'selectedGA[0]': session,
            'selectedChamberId': self.chamber_codes[chamber],
            'coSponsorCheck': 'True',
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
