from __future__ import division
from datetime import datetime
import re
import lxml.html
import requests
import actions
import json
import math
from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin

class DEBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'de'
    categorizer = actions.Categorizer()
    chamber_codes = {'upper':1, 'lower': 2}
    chamber_codes_rev = {1:'upper', 2:'lower'}
    chamber_map = {'House': 'lower', 'Senate': 'upper'}
    legislators = {}
    legislators_by_short = {}

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
        response = self.post(url=search_form_url, data=form, allow_redirects=True)    
        page = json.loads(response.content)
        #print json.dumps(page, indent=4)
        if int(page['Total']) > 0:
            for row in page['Data']:
                self.legislators[ str(row['PersonId']) ] = row
                self.legislators_by_short[ str(row['ShortName']) ] = row
        else:
            self.warning("Error returning legislator list!")

    def scrape_fiscal_note(self, bill, link):
        #https://legis.delaware.gov/json/BillDetail/GetHtmlDocument?fileAttachmentId=48095
        # The DE site for some reason POSTS to an endpoint for fiscal notes
        # then pops the JSON response into a new window.
        # But the attachment endpoint for bill versions works fine.
        attachment_id = link.replace('GetFiscalNoteHtmlDocument(event, ','').replace(')','')
        fn_url = 'https://legis.delaware.gov/json/BillDetail/GetHtmlDocument?fileAttachmentId={}'.format(attachment_id)
        bill.add_document(name='Fiscal Note',mimetype='text/html',url=fn_url)

    def scrape_votes(self, bill, legislation_id):
        votes_url = 'https://legis.delaware.gov/json/BillDetail/GetVotingReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        response = self.post(url=votes_url, data=form, allow_redirects=True)
        if response.content:
            page = json.loads(response.content)
            if page['Total'] > 0:
                for row in page['Data']:
                    self.scrape_vote(bill, row['RollCallId'])

    def scrape_vote(self, bill, vote_id):
        vote_url = 'https://legis.delaware.gov/json/RollCall/GetRollCallVoteByRollCallId'
        form = {
            'rollCallId': vote_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        response = self.post(url=vote_url, data=form, allow_redirects=True)
        if response.content:
            page = json.loads(response.content)
            roll = page['Model']
            vote_chamber = self.chamber_map[roll['ChamberName']]
            #"7/1/16 01:00 AM"
            vote_date = datetime.strptime(roll['TakenAtDateTime'], '%m/%d/%y %I:%M %p')

            #TODO: What does this code mean?
            vote_motion = roll['RollCallVoteType']

            vote_passed = True if roll['RollCallStatus'] == 'Passed' else False
            other_count = int(roll['NotVotingCount']) + int(roll['VacantVoteCount']) + int(roll['AbsentVoteCount']) + int(roll['ConflictVoteCount'])

            vote = Vote(chamber=vote_chamber,
                        date=vote_date,
                        motion=vote_motion,
                        passed=vote_passed,
                        yes_count=roll['YesVoteCount'],
                        no_count=roll['NoVoteCount'],
                        other_count=other_count)

            for row in roll['AssemblyMemberVotes']:
                # AssemblyMemberId looks like it should work here,
                # but for some sessions it's bugged to only return session
                voter = self.legislators_by_short[str(row['ShortName'])]
                if row['SelectVoteTypeCode'] == 'Y':
                    vote.yes(voter['DisplayName'])
                elif row['SelectVoteTypeCode'] == 'N':
                    vote.no(voter['DisplayName'])
                else:
                    vote.other(voter['DisplayName'])

            bill.add_vote(vote)

    def scrape_bill(self, row, chamber, session):

        bill_id = row['LegislationNumber']
        bill_summary = row['Synopsis']
        bill_title = row['LongTitle']
        if row['ShortTitle']:
            alternate_title = row['ShortTitle']

        bill_type = self.classify_bill(bill_id)

        bill = Bill(
            session=session,
            chamber=chamber,
            bill_id=bill_id,
            title=bill_title,
            type=bill_type,
            summary=bill_summary,
        )

        if row['SponsorPersonId']:
            self.add_sponsor_by_legislator_id(bill, row['SponsorPersonId'], 'primary')

        #TODO: Is there a way get additional sponsors and cosponsors, and versions/fns via API?
        html_url = 'https://legis.delaware.gov/BillDetail?LegislationId={}'.format(row['LegislationId'])
        bill.add_source(html_url, mimetype='text/html')

        html = self.lxmlize(html_url)

        #Additional Sponsors: '//label[text()="Additional Sponsor(s):"]/following-sibling::div/a'
        additional_sponsors = html.xpath('//label[text()="Additional Sponsor(s):"]/following-sibling::div/a/@href')
        for sponsor_url in additional_sponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?personId=', '')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'primary')

        #CoSponsors: '//label[text()="Co-Sponsor(s):"]/following-sibling::div/a'
        cosponsors = html.xpath('//label[text()="Additional Sponsor(s):"]/following-sibling::div/a/@href')
        for sponsor_url in cosponsors:
            sponsor_id = sponsor_url.replace('https://legis.delaware.gov/LegislatorDetail?personId=','')
            self.add_sponsor_by_legislator_id(bill, sponsor_id, 'cosponsor')

        versions = html.xpath('//label[text()="Original Text:"]/following-sibling::div/a/@href')
        for version in versions:
            mimetype = self.mime_from_link(version)
            name = 'Bill Text'
            bill.add_version(name=name, url=version, mimetype=mimetype)

        fiscals = html.xpath('//div[contains(@class,"fiscalNote")]/a/@href')
        for fiscal in fiscals:
            self.scrape_fiscal_note(bill, fiscal)

        self.scrape_actions(bill, row['LegislationId'])
        self.scrape_votes(bill, row['LegislationId'])

        print bill
        self.save_bill(bill)

    def add_sponsor_by_legislator_id(self, bill, legislator_id, sponsor_type):
        sponsor = self.legislators[ str(legislator_id)]
        sponsor_name = sponsor['DisplayName']
        sponsor_district = sponsor['DistrictNumber']
        chamber = self.chamber_codes_rev[sponsor['ChamberId']]
        bill.add_sponsor(type=sponsor_type,
                         name=sponsor_name,
                         district=sponsor_district,
                         chamber=chamber)

    def scrape_actions(self, bill, legislation_id):
        actions_url = 'https://legis.delaware.gov/json/BillDetail/GetRecentReportsByLegislationId'
        form = {
            'legislationId': legislation_id,
            'sort': '',
            'group': '',
            'filter': '',
        }
        response = self.post(url=actions_url, data=form, allow_redirects=True)
        page = json.loads(response.content)
        #print json.dumps(page, indent=4)
        for row in page['Data']:
            action_name = row['ActionDescription']
            action_date = datetime.strptime(row['OccuredAtDateTime'], '%m/%d/%y')
            
            if row['ChamberName'] != None:
                action_chamber = self.chamber_map[row['ChamberName']]
            elif 'Senate' in row['ActionDescription']:
                action_chamber = 'upper'
            elif 'House' in row['ActionDescription']:
                action_chamber = 'lower'
            else:
                action_chamber = ''

            attrs = self.categorizer.categorize(action_name)

            bill.add_action(actor=action_chamber,
                            action=action_name,
                            date=action_date,
                            **attrs)

    def classify_bill(self, bill_id):
        legislation_types = {
            'House Bill': 'HB',
            'House Concurrent Resolution': 'HCR',
            'House Joint Resolution': 'HJR',
            'House Resolution': 'HR',
            'Senate Bill': 'SB',
            'Senate Concurrent Resolution': 'SCR',
            'Senate Joint Resolution': 'SJR',
            'Senate Resolution': 'SR',
        }
        for name, abbr in legislation_types.items():
            if abbr in bill_id:
                return name

        return ''

    def scrape(self,chamber,session):
        self.scrape_legislators(session)

        per_page = 20
        page = self.post_search(session, chamber, 1, per_page)
        #print json.dumps(page, indent=4)

        max_results = int(page["Total"])
        if max_results > per_page:
            max_page = int(math.ceil(max_results / per_page))

            for i in range(2, max_page):
                page = self.post_search(session, chamber, i, per_page)

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
        response = self.post(url=search_form_url, data=form, allow_redirects=True)
        page = json.loads(response.content)
        for row in page['Data']:
            self.scrape_bill(row, chamber, session)

        #Return the page object so we can use it to calculate max results    
        return page

    def mime_from_link(self, link):
        if 'HtmlDocument' in link:
            return 'text/html'
        elif 'PdfDocument' in link:
            return 'application/pdf'
        elif 'WordDocument' in link:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            return ''
