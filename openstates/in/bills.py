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

    def make_html_source(self,session,bill_id):
        url = "http://iga.in.gov/legislative/{}/".format(session)
        urls = {
            "hb":"bills/house/",
            "hr":"resolutions/house/simple/",
            "hcr":"resolutions/house/concurrent",
            "hjr":"resolutions/house/joint",
            "hc":"resolutions/house/concurrent",
            "hj":"resolutions/house/joint",
            "sb":"bills/senate/",
            "sr":"resolutions/senate/simple/",
            "scr":"resolutions/senate/concurrent",
            "sjr":"resolutions/senate/joint",
            "sc":"resolutions/senate/concurrent",
            "sj":"resolutions/senate/joint"
            }
        bill_id = bill_id.lower()
        try:
            int(bill_id[2])
        except ValueError:
            bill_prefix = bill_id[:3]
            bill_num = bill_id[3:]
        else:
            bill_prefix = bill_id[:2]
            bill_num = bill_prefix[2:]

        try:
            url += urls[bill_prefix]
        except KeyError:
            raise AssertionError("Unknown bill type {}, don't know how to make url".format(bill_id))
        url += bill_num
        return url

    def get_name(self,random_json):
        #got sick of doing this everywhere
        return random_json["firstName"] + " " + random_json["lastName"]

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
            #sometimes title is blank
            #if that's the case, we can check to see if
            #the latest version has a short description
            if not title:
                title = bill_json["latestVersion"]["shortDescription"]

            #and if that doesn't work, use the bill_id but throw a warning
            if not title:
                title = bill_id
                self.logger.warning("Bill is missing a title, using bill id instead.")


            original_chamber = "lower" if bill_json["originChamber"].lower() == "house" else "upper"
            bill = Bill(session,original_chamber,bill_id,title)
            
            bill.add_source(api_source,note="API key needed")
            bill.add_source(self.make_html_source(session,bill_id))
            #documents/versions


            #sponsors
            positions = {"Representative":"lower","Senator":"upper"}
            for s in bill_json["authors"]:
                bill.add_sponsor("primary",
                    self.get_name(s),
                    chamber=positions[s["position_title"]],
                    official_type="author")

            for s in bill_json["coauthors"]:
                bill.add_sponsor("cosponsor",
                    self.get_name(s),
                    chamber=positions[s["position_title"]],
                    official_type="coauthor")

            for s in bill_json["sponsors"]:
                bill.add_sponsor("primary",
                    self.get_name(s),
                    chamber=positions[s["position_title"]],
                    official_type="sponsor")

            for s in bill_json["cosponsors"]:
                bill.add_sponsor("cosponsor",
                    self.get_name(s),
                    chamber=positions[s["position_title"]],
                    official_type="cosponsor")

            #votes



            self.save_bill(bill)




