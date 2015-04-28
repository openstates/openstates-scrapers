import re
import datetime
import lxml.html
import json

import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class DCBillScraper(BillScraper):
    jurisdiction = 'dc'

    def decode_json(self,stringy_json):
        #the "json" they send is recursively string-encoded.
        if type(stringy_json) == dict:
            for key in stringy_json:
                stringy_json[key] = self.decode_json(stringy_json[key])

        elif type(stringy_json) == list:
            for i in range(len(stringy_json)):
                stringy_json[i] = self.decode_json(stringy_json[i])

        elif type(stringy_json) in (str,unicode):
            if len(stringy_json) > 0 and stringy_json[0] in ["[","{",u"[",u"{"]:
                return self.decode_json(json.loads(stringy_json))
        return stringy_json



    def scrape(self, session, chambers):
        #get member id matching for vote parsing
        member_ids = self.get_member_ids()[session]
        per_page = 10 #seems like it gives me 10 no matter what.
        start_record = 0

        headers = {"Content-Type":"application/json"}
        url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicAdvancedSearch"
        bill_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicData"
        params = {"request":{"sEcho":2,"iColumns":4,"sColumns":"","iDisplayStart":0,"iDisplayLength":per_page,"mDataProp_0":"ShortTitle","mDataProp_1":"Title","mDataProp_2":"LegislationCategories","mDataProp_3":"Modified","iSortCol_0":0,"sSortDir_0":"asc","iSortingCols":0,"bSortable_0":"true","bSortable_1":"true","bSortable_2":"true","bSortable_3":"true"},"criteria":{"Keyword":"","Category":"","SubCategoryId":"","RequestOf":"","CouncilPeriod":str(session),"Introducer":"","CoSponsor":"","CommitteeReferral":"","CommitteeReferralComments":"","StartDate":"","EndDate":"","QueryLimit":100,"FilterType":"","Phases":"","LegislationStatus":"0","IncludeDocumentSearch":"false"}}
        param_json = json.dumps(params)
        response = self.post(url,headers=headers,data=param_json)
        #the response is a terrible string-of-nested-json-strings. Yuck.
        response = self.decode_json(response.json()["d"])
        data = response["aaData"]
        
        global bill_versions

        while len(data) > 0:

            for bill in data:
                bill_versions = [] #sometimes they're in there more than once, so we'll keep track

                bill_id = bill["Title"]
                if bill_id.startswith("AG"):
                    #actually an agenda, skip
                    continue
                bill_params = {"legislationId":bill_id}
                bill_info = self.post(bill_url,headers=headers,data=json.dumps(bill_params))
                bill_info = self.decode_json(bill_info.json()["d"])["data"]
                bill_source_url = "http://lims.dccouncil.us/Legislation/"+bill_id


                legislation_info = bill_info["Legislation"][0]
                title = legislation_info["ShortTitle"]
                
                
                
                if bill_id.startswith("R") or bill_id.startswith("CER"):
                    bill_type = "resolution"
                else:
                    bill_type = "bill"
                
                #dc has no chambers. calling it all upper
                bill = Bill(session,"upper", bill_id, title, type=bill_type)

                #sponsors and cosponsors
                introducers = legislation_info["Introducer"]
                try:
                    #sometimes there are cosponsors, sometimes not.
                    cosponsors = legislation_info["CoSponsor"]
                except KeyError:
                    cosponsors = []
                for i in introducers:
                    sponsor_name = i["Name"]
                    #they messed up Phil Mendelson's name
                    if sponsor_name == "Phil Pmendelson":
                        sponsor_name = "Phil Mendelson"
                    bill.add_sponsor(name=sponsor_name,type="primary")
                for s in cosponsors:
                    sponsor_name = s["Name"]
                    if sponsor_name == "Phil Pmendelson":
                        sponsor_name = "Phil Mendelson"
                    bill.add_sponsor(name=sponsor_name,type="cosponsor")


                #if it's become law, add the law number as an alternate title
                if "LawNumber" in legislation_info:
                    law_num = legislation_info["LawNumber"]
                    if law_num:
                        bill.add_title(law_num)

                #also sometimes it's got an act number
                if "ActNumber" in legislation_info:
                    act_num = legislation_info["ActNumber"]
                    if act_num:
                        bill.add_title(act_num)

                #sometimes AdditionalInformation has a previous bill name
                if "AdditionalInformation" in legislation_info:
                    add_info = legislation_info["AdditionalInformation"]
                    if "previously" in add_info.lower():
                        prev_title = add_info.lower().replace("previously","").strip().replace(" ","")
                        bill.add_title(prev_title.upper())
                    elif add_info:
                        bill["additional_information"] = add_info

                if "WithDrawnDate" in legislation_info:
                    withdrawn_date = self.date_format(legislation_info["WithDrawnDate"])
                    withdrawn_by = legislation_info["WithdrawnBy"][0]["Name"].strip()
                    if withdrawn_by == "the Mayor":

                        bill.add_action("executive",
                                    "withdrawn",
                                    withdrawn_date,
                                    "bill:withdrawn")

                    elif "committee" in withdrawn_by.lower():
                        bill.add_action("upper",
                                    "withdrawn",
                                    withdrawn_date,
                                    "bill:withdrawn",
                                    committees=withdrawn_by)
                    else:
                        bill.add_action("upper",
                                    "withdrawn",
                                    withdrawn_date,
                                    "bill:withdrawn",
                                    legislators=withdrawn_by)


                #deal with actions involving the mayor
                mayor = bill_info["MayorReview"]
                if mayor != []:
                    mayor = mayor[0]

                    #in dc, mayor == governor because openstates schema
                    if "TransmittedDate" in mayor:
                        transmitted_date = self.date_format(mayor["TransmittedDate"])

                        bill.add_action("executive",
                                    "transmitted to mayor",
                                    transmitted_date,
                                    type = "governor:received")

                    if 'SignedDate' in mayor:
                        signed_date = self.date_format(mayor["SignedDate"])

                        bill.add_action("executive",
                                        "signed",
                                        signed_date,
                                        type="governor:signed")


                    elif 'ReturnedDate' in mayor: #if returned but not signed, it was vetoed
                        veto_date = self.date_format(mayor["ReturnedDate"])

                        bill.add_action("executive",
                                        "vetoed",
                                        veto_date,
                                        type="governor:vetoed")

                        if 'EnactedDate' in mayor: #if it was returned and enacted but not signed, there was a veto override
                            override_date = self.date_format(mayor["EnactedDate"])

                            bill.add_action("upper",
                                        "veto override",
                                        override_date,
                                        type="bill:veto_override:passed")

                    if 'AttachmentPath' in mayor:
                        #documents relating to the mayor's review
                        self.add_documents(mayor["AttachmentPath"],bill)

                congress = bill_info["CongressReview"]
                if len(congress) > 0:
                    congress = congress[0]
                    if "TransmittedDate" in congress:
                        transmitted_date = self.date_format(congress["TransmittedDate"])

                        bill.add_action("other",
                                    "Transmitted to Congress for review",
                                    transmitted_date)




                #deal with committee actions
                if "DateRead" in legislation_info:
                    date = legislation_info["DateRead"]
                elif "IntroductionDate" in legislation_info:
                    date = legislation_info["IntroductionDate"]
                else:
                    self.logger.warning("Crap, we can't find anything that looks like an action date. Skipping")
                    continue
                date = self.date_format(date)
                if "CommitteeReferral" in legislation_info:
                    committees = []
                    for committee in legislation_info["CommitteeReferral"]:
                        if committee["Name"].lower() == "retained by the council":
                            committees = []
                            break
                        else:
                            committees.append(committee["Name"])
                    if committees != []:
                        bill.add_action("upper",
                                    "referred to committee",
                                    date,
                                    committees=committees,
                                    type="committee:referred")

                if "CommitteeReferralComments" in legislation_info:
                    committees = []
                    for committee in legislation_info["CommitteeReferralComments"]:
                        committees.append(committee["Name"])
                    bill.add_action("upper",
                                    "comments from committee",
                                    date,
                                    committees=committees,
                                    type="other")

                #deal with random docs floating around
                docs = bill_info["OtherDocuments"]
                for d in docs:
                    if "AttachmentPath" in d:
                        self.add_documents(d["AttachmentPath"],bill)
                    else:
                        self.logger.warning("Document path missing from 'Other Documents'")

                if "MemoLink" in legislation_info:
                    self.add_documents(legislation_info["MemoLink"],bill)

                if "AttachmentPath" in legislation_info:
                    self.add_documents(legislation_info["AttachmentPath"],bill)


                #full council votes
                votes = bill_info["VotingSummary"]
                for vote in votes:
                    self.process_vote(vote, bill, member_ids)
     

                #deal with committee votes
                if "CommitteeMarkup" in bill_info:
                    committee_info = bill_info["CommitteeMarkup"]
                    if len(committee_info) > 0:
                        for committee_action in committee_info:
                            self.process_committee_vote(committee_action,bill)
                        if "AttachmentPath" in committee_info:
                            self.add_documents(vote["AttachmentPath"],bill,is_version)

                bill.add_source(bill_source_url)
                self.save_bill(bill)
            
            #get next page
            start_record += per_page
            params["request"]["iDisplayStart"] = start_record
            param_json = json.dumps(params)
            response = self.post(url,headers=headers,data=param_json)
            response = self.decode_json(response.json()["d"])
            data = response["aaData"]
    
    def get_member_ids(self):
        member_dict = {} #three levels: from session to member_id to name
        search_data_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicSearchData"
        response = self.post(search_data_url,headers={"Content-Type":"application/json"})
        member_data = self.decode_json(response.json()['d'])["Members"]
        for session_id, members in member_data.items():
            member_dict[session_id] = {}
            for member in members:
                member_id = int(member["ID"]) #should be ints already, but once one wasn't
                member_name = member["MemberName"]
                member_dict[session_id][member_id] = member_name

        return member_dict


    def process_vote(self, vote, bill, member_ids):
        try:
            motion = vote["ReadingDescription"]
        except KeyError:
            self.logger.warning("Can't even figure out what we're voting on. Skipping.")
            return

        if not "VoteResult" in vote:
            if "postponed" in motion.lower():
                result = "Postponed"
                status = True #because we're talking abtout the motion, not the amendment
            elif "tabled" in motion.lower():
                result = "Tabled"
                status = True
            else:
                self.logger.warning("Could not find result of vote, skipping.")
                return
        else:

            result = vote["VoteResult"]    

            statuses = {"approved":True,
                    "disapproved":False,
                    "failed":False,
                    "declined":False,
                    "passed":True}

            try:
                status = statuses[result.strip().lower()]
            except KeyError:
                self.logger.warning("Unexpected vote result '{result},' skipping vote.".format(result=result))
                return

        date = self.date_format(vote["DateOfVote"])

        leg_votes = vote["MemberVotes"]
        v = Vote('upper',date,motion,status,0,0,0,
                yes_votes=[],no_votes=[],other_votes=[])
        for leg_vote in leg_votes:
            mem_name = member_ids[int(leg_vote["MemberId"])]
            if leg_vote["Vote"] == "1":
                v['yes_count'] += 1
                v['yes_votes'].append(mem_name)
            elif leg_vote["Vote"] == "2":
                v['no_count'] += 1
                v['no_votes'].append(mem_name)
            else:
                v['other_count'] += 1
                v['other_votes'].append(mem_name)

        

        #the documents for the readings are inside the vote
        #level in the json, so we'll deal with them here
        #and also add relevant actions

        if "amendment" in motion.lower():
            if status:
                t = "amendment:passed"
            elif result in ["Tabled","Postponed"]:
                t = "amendment:tabled"
            else:
                t = "amendment:failed"
        elif result in ["Tabled","Postponed"]:
                t = "other" #we don't really have a thing for postponed bills
        elif "first reading" in motion.lower():
            t = "bill:reading:1"
        elif "1st reading" in motion.lower():
            t = "bill:reading:1"
        elif "second reading" in motion.lower():
            t = "bill:reading:2"
        elif "2nd reading" in motion.lower():
            t = "bill:reading:2"
        elif "third reading" in motion.lower():
            t = "bill:reading:3"
        elif "3rd reading" in motion.lower():
            t = "bill:reading:3"
        elif "final reading" in motion.lower():
            t = "bill:reading:3"
        else:
            t = "other"
        
        bill.add_action("upper",
                        motion,
                        date,
                        type=t)

        if "amendment" in t:
            vote["type"] = "amendment"
        elif "reading" in t:
            vote["type"] = t.replace("bill:","")

        #some documents/versions are hiding in votes.
        if "AttachmentPath" in vote:
            is_version = False
            try:
                if vote["DocumentType"] in ["enrollment","engrossment","introduction"]:
                    is_version = True
            except KeyError:
                pass

            if motion in ["enrollment","engrossment","introduction"]:
                is_version = True

            self.add_documents(vote["AttachmentPath"],bill,is_version)

        bill.add_vote(v)

        

    def process_committee_vote(self,committee_action,bill):
        try:
            date = committee_action["ActionDate"]
            vote_info = committee_action["Vote"]

        except KeyError:
            self.logger.warning("Committee vote has no data. Skipping.")
            return
        date = self.date_format(date)

        other_count = 0
        for v in vote_info:
            vote_count = 0 if v["VoteCount"] == "" else int(v["VoteCount"])

            if v["VoteType"] == "Yes":
                yes_count = vote_count
            elif v["VoteType"] == "No":
                no_count = vote_count
            else:
                other_count += vote_count

        passed = False
        if yes_count > no_count:
            passed = True

        vote = Vote("upper",date,"Committee Vote",passed,yes_count,no_count,other_count)
        bill.add_vote(vote)


    def add_documents(self,attachment_path,bill,is_version=False):
        global bill_versions
        base_url = "http://lims.dccouncil.us/Download/" #nothing is actual links. we'll have to concatenate to get doc paths (documents are hiding in thrice-stringified json. eek.)
        for a in attachment_path:
            doc_type = a["Type"]
            doc_name = a["Name"]
            rel_path = a["RelativePath"]
            if doc_type and doc_name and rel_path:  
                doc_url = base_url+rel_path+"/"+doc_name
            else:
                self.logger.warning("Bad link for document {}".format(doc_name))
                return

            mimetype = "application/pdf" if doc_name.endswith("pdf") else None

            #figure out if it's a version from type/name
            possible_version_types = ["SignedAct","Introduction","Enrollment","Engrossment"]
            for vt in possible_version_types:
                if vt.lower() in doc_name.lower():
                    is_version = True
                    doc_type = vt 

            if "amendment" in doc_name.lower():
                doc_type = "Amendment"

            if is_version:
                if doc_url in bill_versions:
                    self.logger.warning("Version {} has been seen multiple times. Keeping first version seen".format(doc_url))
                else:
                    bill.add_version(doc_type,doc_url,mimetype=mimetype)
                    bill_versions.append(doc_url)
                continue
                    

            bill.add_document(doc_type,doc_url,mimetype=mimetype)

    def date_format(self,d):
        #the time seems to be 00:00:00 all the time, so ditching it with split
        return datetime.datetime.strptime(d.split()[0],"%Y/%m/%d")