import re
import datetime
import os
from collections import OrderedDict

import scrapelib


from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import pytz
import lxml.html

from .actions import Categorizer
from apiclient import ApiClient


class INBillScraper(BillScraper):
    jurisdiction = 'in'

    categorizer = Categorizer()
    _tz = pytz.timezone('US/Eastern')


    def make_html_source(self,session,bill_id):
        url = "http://iga.in.gov/legislative/{}/".format(session)
        urls = {
            "hb":"bills/house/",
            "hr":"resolutions/house/simple/",
            "hcr":"resolutions/house/concurrent/",
            "hjr":"resolutions/house/joint/",
            "hc":"resolutions/house/concurrent/",
            "hj":"resolutions/house/joint/",
            "sb":"bills/senate/",
            "sr":"resolutions/senate/simple/",
            "scr":"resolutions/senate/concurrent/",
            "sjr":"resolutions/senate/joint/",
            "sc":"resolutions/senate/concurrent/",
            "sj":"resolutions/senate/joint/"
            }
        bill_id = bill_id.lower()

        bill_prefix = "".join([c for c in bill_id if c.isalpha()])
        bill_num = "".join([c for c in bill_id if c.isdigit()])

        try:
            url += urls[bill_prefix]
        except KeyError:
            raise AssertionError("Unknown bill type {}, don't know how to make url".format(bill_id))
        url += str(int(bill_num))
        return url



    def get_name(self,random_json):
        #got sick of doing this everywhere
        return random_json["firstName"] + " " + random_json["lastName"]

    def process_votes(self,rollcalls,bill,proxy):

        result_types = {
            'FAILED': False,
            'DEFEATED': False,
            'PREVAILED': True,
            'PASSED': True,
            'SUSTAINED': True,
            'NOT SECONDED': False,
            'OVERRIDDEN': True,
            'ADOPTED': True,
        }

        for r in rollcalls:
            proxy_link = proxy["url"] + r["link"]
            (path, resp) = self.urlretrieve(proxy_link)
            text = convert_pdf(path, 'text')
            lines = text.split("\n")
            os.remove(path)


            chamber = "lower" if "house of representatives" in lines[0].lower() else "upper"
            date_parts = lines[1].strip().split()[-3:]
            date_str = " ".join(date_parts).title() + " " + lines[2].strip()
            vote_date = datetime.datetime.strptime(date_str,"%b %d, %Y %I:%M:%S %p")


            passed = None

            for res,val in result_types.items():
                if res in lines[3].upper():
                    passed = val
                    break

            if passed is None:
                raise AssertionError("Missing bill passage type")

            motion = " ".join(lines[4].split()[:-2])
            try:
                yeas = int(lines[4].split()[-1])
                nays = int(lines[5].split()[-1])
                excused = int(lines[6].split()[-1])
                not_voting = int(lines[7].split()[-1])
            except ValueError:
                self.logger.warning("Vote format is weird, skipping")
                continue
            other_count = excused + not_voting

            vote = Vote(chamber,vote_date,motion,passed,yeas,nays,other_count,yes_votes=[],no_votes=[],other_votes=[])

            vote.add_source(proxy_link)

            currently_counting = ""

            possible_vote_lines = lines[8:]
            for l in possible_vote_lines:
                l = l.replace("NOT\xc2\xa0VOTING","NOT VOTING")
                l = l.replace("\xc2\xa0"," -")
                if "yea-" in l.lower().replace(" ",""):
                    currently_counting = "yes_votes"
                elif "nay-" in l.lower().replace(" ",""):
                    currently_counting = "no_votes"
                elif "excused-" in l.lower().replace(" ",""):
                    currently_counting = "other_votes"
                elif "notvoting-" in l.lower().replace(" ",""):
                    currently_counting = "other_votes"
                elif currently_counting == "":
                    pass
                elif re.search(r'v\. \d\.\d',l):
                    #this gets rid of the version number
                    #which is often found at the bottom of the doc
                    pass
                else:
                    voters = l.split("  ")
                    for v in voters:
                        if v.strip():
                            vote[currently_counting].append(v.strip())

            assert len(vote["yes_votes"]) == vote["yes_count"],\
                "Yes vote counts ({count}) don't match count of actual votes ({actual})".format(count=vote["yes_count"],actual=len(vote["yes_votes"]))
            assert len(vote["no_votes"]) == vote["no_count"],\
                "No vote counts ({count}) don't match count of actual votes ({actual})".format(count=vote["no_count"],actual=len(vote["no_votes"]))
            assert len(vote["other_votes"]) == vote["other_count"],\
                "Other vote counts ({count}) don't match count of actual votes ({actual})".format(count=vote["other_count"],actual=len(vote["other_votes"]))
            

            #indiana only has simple majorities even for veto overrides
            #if passage status isn't the same as yes>no, then we should look!
            if vote["passed"] != (vote["yes_count"] > vote["no_count"]):
                raise AssertionError("Vote count doesn't agree with vote passage status")

            bill.add_vote(vote)

    def deal_with_version(self,version,bill,proxy):
        #documents
        docs = OrderedDict()
        docs["Committee Amendment"] = version["cmte_amendments"]
        docs["Floor Amendment"] = version["floor_amendments"]
        docs["Amendment"] = version["amendments"]
        docs["Fiscal Note"] = version["fiscal-notes"]
        docs["Committee Report"] = version["committee-reports"]

        #sometimes amendments appear in multiple places
        #cmte_amendment vs amendment
        #so we're only adding once but using the more
        #specific if it's available
        urls_seen = []
        for doc_type in docs:
            doc_list = docs[doc_type]
            for doc in doc_list:
                title = "{doc_type}: {name}".format(doc_type=doc_type,name=doc["name"])
                link = proxy["url"] + doc["link"]
                if link not in urls_seen:
                    urls_seen.append(link)
                    bill.add_document(title,link,mimetype="application/pdf")

        #version
        link = proxy["url"] + version["link"]
        name = version["stageVerbose"]
        if link not in urls_seen:
            urls_seen.append(link)
            update_date = version["updated"]
            create_date = version["created"]
            intro_date = version["introduced"]
            file_date = version["filed"]
            for d in [update_date,create_date,intro_date,file_date]:
                try:
                    update_date = datetime.datetime.strptime(d,"%Y-%m-%dT%H:%M:%S")
                except TypeError:
                    continue
                else:
                    break
                
            bill.add_version(name,link,mimetype="application/pdf",date=update_date)

        #votes
        votes = version["rollcalls"]
        self.process_votes(votes,bill,proxy)


    def scrape(self, session, chambers):
        
        api_base_url = "https://api.iga.in.gov"
        proxy = {"url":"http://in.proxy.openstates.org"}
        #ah, indiana. it's really, really hard to find
        #pdfs in their web interface. Super easy with
        #the api, but a key needs to be passed
        #in the headers. To make these documents
        #viewable to the public and our scrapers,
        #sunlight's put up a proxy service at this link
        #using our api key for pdf document access.


        client = ApiClient(self)
        r = client.get("bills",session=session)
        all_pages = client.unpaginate(r)
        for b in all_pages:
            bill_id = b["billName"]
            for idx,char in enumerate(bill_id):
                try:
                    int(char)
                except ValueError:
                    continue
                disp_bill_id = bill_id[:idx]+" "+str(int(bill_id[idx:]))
                break


            bill_link = b["link"]
            api_source = api_base_url + bill_link
            bill_json = client.get("bill",session=session,bill_id=bill_id.lower())
            
            title = bill_json["title"]
            if title == "NoneNone":
                title = None
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
            bill = Bill(session,original_chamber,disp_bill_id,title)
            
            bill.add_source(api_source,note="API key needed")
            bill.add_source(self.make_html_source(session,bill_id))
            

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

            #actions
            action_link = bill_json["actions"]["link"]
            api_source = api_base_url + action_link
            try:
                actions = client.get("bill_actions",session=session,bill_id=bill_id.lower())
            except scrapelib.HTTPError:
                self.logger.warning("Could not find bill actions page")
                actions = {"items":[]}
            for a in actions["items"]:
                action_desc = a["description"]
                if "governor" in action_desc.lower():
                    action_chamber = "executive"
                elif a["chamber"]["name"].lower() == "house":
                    action_chamber = "lower"
                else:
                    action_chamber = "upper"
                date = a["date"]
                date = datetime.datetime.strptime(date,"%Y-%m-%dT%H:%M:%S")
                
                action_type = []
                d = action_desc.lower()
                committee = None

                reading = False
                if "first reading" in d:
                    action_type.append("bill:reading:1")
                    reading = True

                if ("second reading" in d
                    or "reread second time" in d):
                    action_type.append("bill:reading:2")
                    reading = True

                if ("third reading" in d
                    or "reread third time" in d):
                    action_type.append("bill:reading:3")
                    if "passed" in d:
                        action_type.append("bill:passed")
                    if "failed" in d:
                        action_type.append("bill:failed")
                    reading = True

                if "adopted" in d and reading:
                    action_type.append("bill:passed")

                if ("referred" in d and "committee on" in d
                    or "reassigned" in d and "committee on" in d):
                    committee = d.split("committee on")[-1].strip()
                    action_type.append("committee:referred")


                if "committee report" in d:
                    if "pass" in d:
                        action_type.append("committee:passed")
                    if "fail" in d:
                        action_type.append("committee:failed")

                if "amendment" in d and "without amendment" not in d:
                    if "pass" in d or "prevail" in d or "adopted" in d:
                        action_type.append("amendment:passed")
                    if "fail" or "out of order" in d:
                        action_type.append("amendment:failed")
                    if "withdraw" in d:
                        action_type.append("amendment:withdrawn")


                if "signed by the governor" in d:
                    action_type.append("governor:signed")


                if ("not substituted for majority report" in d
                    or "returned to the house" in d
                    or "referred to the senate" in d
                    or "referred to the house" in d
                    or "technical corrections" in d
                    or "signed by the president" in d
                    or "signed by the speaker"
                    or "authored" in d
                    or "sponsor" in d
                    or "coauthor" in d
                    or ("rule" in d and "suspended" in d)
                    or "removed as author" in d
                    or ("added as" in d and "author" in d)
                    or "public law" in d):

                        if len(action_type) == 0:
                            action_type.append("other")

                if len(action_type) == 0:
                    #calling it other and moving on with a warning
                    self.logger.warning("Could not recognize an action in '{}'".format(action_desc))
                    action_type = ["other"]

                elif committee:
                    bill.add_action(action_chamber,action_desc,date,type=action_type,committees=committee)

                else:
                    bill.add_action(action_chamber,action_desc,date,type=action_type)



            #subjects
            subjects = [s["entry"] for s in bill_json["latestVersion"]["subjects"]]
            bill["subjects"] = subjects

            
            #versions and votes
            for version in bill_json["versions"][::-1]:
                version_json = client.get("bill_version",
                                        session=session,
                                        bill_id=version["billName"],
                                        version_id=version["printVersionName"])

                self.deal_with_version(version_json,bill,proxy)



            self.save_bill(bill)

