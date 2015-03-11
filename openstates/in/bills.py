import re
import datetime

import scrapelib
from billy.scrape.bills import BillScraper, Bill

import pytz
import lxml.html

from .actions import Categorizer
from .models import parse_vote, BillDocuments, VoteParseError
from apiclient import ApiClient

def parse_vote_count(s):
    if s == 'NONE':
        return 0
    return int(s)


def insert_specific_votes(vote, specific_votes):
    for name, vtype in specific_votes:
        if vtype == 'yes':
            vote.yes(name)
        elif vtype == 'no':
            vote.no(name)
        elif vtype == 'other':
            vote.other(name)


def check_vote_counts(vote):
    try:
        assert vote['yes_count'] == len(vote['yes_votes'])
        assert vote['no_count'] == len(vote['no_votes'])
        assert vote['other_count'] == len(vote['other_votes'])
    except AssertionError:
        pass


class INBillScraper(BillScraper):
    jurisdiction = 'in'

    categorizer = Categorizer()
    _tz = pytz.timezone('US/Eastern')

    # Can turn this on or off. There are thousands of subjects and it takes hours.
    SCRAPE_SUBJECTS = True

    def scrape(self, session, chambers):
        api_base_url = "https://api.iga.in.gov"
        client = ApiClient(self)
        r = client.get("bills",session=session)
        all_pages = client.unpaginate(r)
        for b in all_pages:
            bill_id = b["billName"]
            bill_link = b["link"]
            api_source = api_base_url + bill_link
            bill_json = client.get("bill",session=session,bill_id=bill_id.lower())
            title = bill_json["title"]
            original_chamber = "lower" if bill_json["originChamber"].lower() == "house" else "upper"
            bill = Bill(session,original_chamber,bill_id,title)
            #sources
            bill.add_source(api_source,note="API key needed")
            #documents/versions
            #sponsors
            #votes
            self.save_bill(bill)




