import re
import json
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from . import utils
from . import action_utils

from lxml import html
from lxml import etree

BASE_URL = 'http://www.azleg.gov/'

class AZBillScraper(BillScraper):

    """
    Arizona Bill Scraper.
    """
    jurisdiction = 'az'
    chamber_map = {'lower':'H', 'upper':'S'}

    def get_session_id(self, session):
        """
        returns the session id for a given session
        """
        return self.metadata['session_details'][session]['session_id']

    def scrape_bill(self, chamber, session, bill_id):
        """
        Scrapes documents, actions, vote counts and votes for
        a given bill.
        """
        session_id = self.get_session_id(session)
        bill_json_url = 'https://apps.azleg.gov/api/Bill/?billNumber={}&sessionId={}&legislativeBody={}'.format(bill_id, session_id, self.chamber_map[chamber])
        response = self.get(bill_json_url)
        page = json.loads(response.content)

        bill_title = page['ShortTitle']
        bill_id = page['Number']
        internal_id = page['BillId']
        bill_type = self.get_bill_type(bill_id)

        bill = Bill(
            session=session,
            chamber=chamber,
            bill_id=bill_id,
            title=bill_title,
            type=bill_type
        )
        self.scrape_actions(bill, page)
        self.scrape_versions(bill, internal_id)
        self.scrape_sponsors(bill, internal_id)
        self.scrape_subjects(bill, internal_id)

        bill_url = 'https://apps.azleg.gov/BillStatus/BillOverview/{}?SessionId={}'.format(internal_id, session_id)
        bill.add_source(bill_url)

        bill = self.sort_bill_actions(bill)

        self.save_bill(bill)
        #print json.dumps(page, indent=4)


    def scrape_versions(self, bill, internal_id):
        # Careful, this sends XML to a browser but JSON to machines
        # https://apps.azleg.gov/api/DocType/?billStatusId=68408
        versions_url = 'https://apps.azleg.gov/api/DocType/?billStatusId={}'.format(internal_id)
        page = json.loads(self.get(versions_url).content)
        if page and 'Documents' in page[0]:
            for doc in page[0]['Documents']:
                bill.add_version(
                    name=doc['DocumentName'],
                    url=doc['HtmlPath'],
                    mimetype='text/html'
                )

    def scrape_sponsors(self, bill, internal_id):
        # Careful, this sends XML to a browser but JSON to machines
        # https://apps.azleg.gov/api/BillSponsor/?id=68398
        sponsors_url = 'https://apps.azleg.gov/api/BillSponsor/?id={}'.format(internal_id)
        page = json.loads(self.get(sponsors_url).content)
        for sponsor in page:
            if 'Prime' in sponsor['SponsorType']:
                sponsor_type = 'primary'
            else:
                sponsor_type = 'cosponsor'
        
        #Some older bills don't have the FullName key
        if 'FullName' in sponsor['Legislator']:
            sponsor_name = sponsor['Legislator']['FullName']
        else:
            sponsor_name = "{} {}".format(sponsor['Legislator']['FirstName'], sponsor['Legislator']['LastName'])

        bill.add_sponsor(
            type=sponsor_type,
            name=sponsor_name
        )

    def scrape_subjects(self, bill, internal_id):
        # https://apps.azleg.gov/api/Keyword/?billStatusId=68149
        subjects_url = 'https://apps.azleg.gov/api/Keyword/?billStatusId={}'.format(internal_id)
        page = json.loads(self.get(subjects_url).content)
        subjects = []
        for subject in page:
            subjects.append(subject['Name'])
        bill['subjects'] = subjects

    def scrape_actions(self, bill, page):
        """
        Scrape the actions for a given bill

        AZ No longer provides a full list, just a series of keys and dates.
        So map that backwards using action_map
        """
        for action in action_utils.action_map:
            if page[action] and action_utils.action_map[action]['name'] != '':
                print page[action]
                try:
                    action_date = datetime.datetime.strptime(page[action], '%Y-%m-%dT%H:%M:%S')
                    bill.add_action(
                        actor=self.actor_from_action(bill, action),
                        action=action_utils.action_map[action]['name'],
                        date=action_date,
                        type=action_utils.action_map[action]['action']
                    )
                except ValueError:
                    self.warning("Invalid Action Time {} for {}".format(page[action], action))
                


    def actor_from_action(self, bill, action):
        """
        Determine the actor from the action key  
        If the action_map = 'chamber', return the bill's home chamber
        """
        action_map = action_utils.action_chamber_map
        for key in action_map:
            if key in action:
                if action_map[key] == 'chamber':
                    return bill['chamber']
                else:
                    return action_map[key]

    def scrape(self, chamber, session):
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)
   
        #Get the bills page to start the session
        req = self.get('http://www.azleg.gov/bills/')

        session_form_url = 'http://www.azleg.gov/azlegwp/setsession.php'
        form = {
            'sessionID': session_id
        }
        req = self.post(url=session_form_url, data=form, cookies=req.cookies, allow_redirects=True)
        
        bill_list_url = 'http://www.azleg.gov/bills/'
        
        page = self.get(bill_list_url, cookies=req.cookies).content
        # There's an errant close-comment that browsers handle 
        # but LXML gets really confused.
        page = page.replace('--!>','-->')
        page = html.fromstring(page)

        bill_rows = []
        if(chamber == 'lower'):
            bill_rows = page.xpath('//div[@name="HBTable"]//tbody//tr')
            for row in bill_rows:
                bill_id = row.xpath('td/a/text()')[0]
                self.scrape_bill(chamber, session, bill_id)

        elif (chamber == 'upper'):
            bill_rows = page.xpath('//div[@name="SBTable"]//tbody//tr')
            for row in bill_rows:
                bill_id = row.xpath('td/a/text()')[0]
                self.scrape_bill(chamber, session, bill_id)
 
        #TODO: MBTable - Non-bill Misc Motions?



    def sort_bill_actions(self, bill):
        actions = bill['actions']
        actions_list = []
        out_of_order = []
        new_list = []
        if not actions:
            return bill
        action_date = actions[0]['date']
        actions[0]['action'] = actions[0]['action'].lower()
        actions_list.append(actions[0])
        # seperate the actions that are out of order
        for action in actions[1:]:
            if action['date'] < action_date:
                out_of_order.append(action)
            else:
                actions_list.append(action)
                action_date = action['date']
            action['action'] = action['action'].lower()
        action_date = actions_list[0]['date']


        for action in actions_list:
            # this takes care of the actions in beween
            for act in out_of_order:
                if act['date'] < action_date:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))
                if act['date'] >= action_date and act['date'] < action['date']:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))
            new_list.append(action)

            for act in out_of_order:
                if act['date'] == action['date']:
                    o_index = out_of_order.index(act)
                    new_list.append(out_of_order.pop(o_index))

        if out_of_order != []:
            self.log("Unable to sort " + bill['bill_id'])
            return bill
        else:
            bill['actions'] = new_list
            return bill

    def get_bill_type(self, bill_id):
        for key in utils.bill_types:
            if key in bill_id.lower():
                return utils.bill_types[key]

        return False
