import re
import datetime
import lxml.html
import json

import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class DCBillScraper(BillScraper):
    jurisdiction = 'dc'

    #TODO: 
        #2) poke around for other kinds of actions (incl congress)

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

        base_url = "http://lims.dccouncil.us/" #nothing is actual links. we'll have to concatenate to get doc paths (documents are hiding in thrice-stringified json. eek.)
        headers = {"Content-Type":"application/json"}
        url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicAdvancedSearch"
        bill_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicData"
        params = {"request":{"sEcho":2,"iColumns":4,"sColumns":"","iDisplayStart":0,"iDisplayLength":per_page,"mDataProp_0":"ShortTitle","mDataProp_1":"Title","mDataProp_2":"LegislationCategories","mDataProp_3":"Modified","iSortCol_0":0,"sSortDir_0":"asc","iSortingCols":0,"bSortable_0":"true","bSortable_1":"true","bSortable_2":"true","bSortable_3":"true"},"criteria":{"Keyword":"","Category":"","SubCategoryId":"","RequestOf":"","CouncilPeriod":str(session),"Introducer":"","CoSponsor":"","ComitteeReferral":"","CommitteeReferralComments":"","StartDate":"","EndDate":"","QueryLimit":100,"FilterType":"","Phases":"","LegislationStatus":"0","IncludeDocumentSearch":"false"}}
        param_json = json.dumps(params)
        response = self.post(url,headers=headers,data=param_json)
        #the response is a terrible string-of-nested-json-strings. Yuck.
        response = self.decode_json(response.json()["d"])
        data = response["aaData"]
        
        bill_versions = [] #sometimes they're in there more than once, so we'll keep track

        while len(data) > 0:

            for bill in data:
                bill_id = bill["Title"]
                if bill_id.startswith("AG"):
                    #actually an agenda, skip
                    continue
                bill_params = {"legislationId":bill_id}
                bill_info = self.post(bill_url,headers=headers,data=json.dumps(bill_params))
                bill_info = self.decode_json(bill_info.json()["d"])["data"]
                filename = "/home/rachel/dc_json_temps/{}.txt".format(bill_id)
                with open(filename, "w") as f:

                    f.write(json.dumps(bill_info))


                legislation_info = bill_info["Legislation"][0]
                title = legislation_info["ShortTitle"]
                print title
                
                docs = bill_info["OtherDocuments"]
                
                
                #dc has no chambers. calling it all upper
                bill = Bill(session,"upper", bill_id, title)

                introducers = legislation_info["Introducer"]
                try:
                    cosponsors = legislation_info["CoSponsor"]
                except KeyError:
                    cosponsors = []
                for i in introducers:
                    sponsor_name = i["Name"]
                    bill.add_sponsor(name=sponsor_name,type="primary")
                for s in cosponsors:
                    sponsor_name = s["Name"]
                    bill.add_sponsor(name=sponsor_name,type="cosponsor")

                #deal with actions involving the mayor
                mayor = bill_info["MayorReview"]
                if mayor != []:
                    mayor = mayor[0]

                    #in dc, mayor == governor
                    if "TransmittedDate" in mayor:
                        transmitted_date = mayor["TransmittedDate"].split(" ")[0]
                        transmitted_date = datetime.datetime.strptime(transmitted_date,"%Y/%m/%d")

                        bill.add_action("mayor",
                                    "transmitted to mayor",
                                    transmitted_date,
                                    type = "governor:received")

                    if 'SignedDate' in mayor:
                        signed_date = mayor["SignedDate"].split(" ")[0]
                        signed_date = datetime.datetime.strptime(signed_date,"%Y/%m/%d")

                        bill.add_action("mayor",
                                        "signed",
                                        signed_date,
                                        type="governor:signed")



                    elif 'ReturnedDate' in mayor: #if returned but not signed, it was vetoed
                        veto_date = mayor["ReturnedDate"].split(" ")[0]
                        veto_date = datetime.datetime.strptime(veto_date,"%Y/%m/%d")

                        bill.add_action("mayor",
                                        "vetoed",
                                        veto_date,
                                        type="governor:vetoed")

                        if 'EnactedDate' in mayor: #if it was returned and enacted but not signed, there was a veto override
                            override_date = mayor["EnactedDate"].split(" ")[0]
                            override_date = datetime.datetime.strptime(override_date,"%Y/%m/%d")

                            bill.add_action("upper",
                                        "veto override",
                                        override_date,
                                        type="bill:veto_override:passed")

                    if 'AttachmentPath' in mayor:
                        for a in mayor["AttachmentPath"]:
                            for a in mayor["AttachmentPath"]:
                                doc_type = a["Type"]
                                doc_name = a["Name"]
                                rel_path = a["RelativePath"]
                                doc_url = base_url+"Download/"+rel_path+"/"+doc_name
                                if doc_type == "SignedAct":
                                    if not doc_url in bill_versions:
                                        bill_versions.append(doc_url)
                                        bill.add_version(doc_type,doc_url,mimetype="application/pdf")
                                        
                                else:
                                    bill.add_document(doc_type,doc_url,mimetype="application/pdf")

                congress = bill_info["CongressReview"]
                if len(congress) > 0:
                    congress = congress[0]
                    if "TransmittedDate" in congress:
                        transmitted_date = congress["TransmittedDate"].split()[0]
                        transmitted_date = datetime.datetime.strptime(transmitted_date,"%Y/%m/%d")
                        bill.add_action("US Congress",
                                    "Transmitted to Congress for review",
                                    date)


                #deal with committee actions
                if "DateRead" in legislation_info:
                    date = legislation_info["DateRead"].split(" ")[0] #time is always 0
                elif "IntroductionDate" in legislation_info:
                    date = legislation_info["IntroductionDate"].split(" ")[0]
                else:
                    self.logger.warning("Crap, we can't find anything that looks like an action date. Skipping")
                    continue
                date = datetime.datetime.strptime(date,"%Y/%m/%d")
                if "ComitteeReferral" in legislation_info: #their typo, not mine
                    committees = []
                    for committee in legislation_info["ComitteeReferral"]:
                        if committee["Name"] == "Retained by the council":
                            committees = []
                            break
                        else:
                            committees.append(committee["Name"])
                    if committees != []:
                        bill.add_action("committee",
                                    "referred to committee",
                                    date,
                                    committees=committees,
                                    type="committee:referred")

                if "CommitteeReferralComments" in legislation_info:
                    committees = []
                    for committee in legislation_info["CommitteeReferralComments"]:
                        committees.append(committee["Name"])
                    bill.add_action("committee",
                                    "retained by council with comments from committees",
                                    date,
                                    committees=committees,
                                    type="other")

                

                #deal with documents

                memos = []
                for doc_type in ["MemoLink","AttachmentPath"]:
                    if doc_type in legislation_info:
                        for d in legislation_info[doc_type]:
                            memos.append(d)
                if "OtherDocuments" in legislation_info: #dealing with documents hiding in "other documents", see PR21-0040
                    for d in legislation_info["OtherDocuments"]:
                        if "AttachmentPath" in d:
                            memos.append(d["AttachmentPath"])
                for memo in memos:
                    memo_name = memo["Name"]
                    memo_url = base_url+"Download/"+memo["RelativePath"]+"/"+memo_name
                    bill.add_document(memo_name,
                                    memo_url,
                                    "pdf")

                votes = bill_info["VotingSummary"]
                for vote in votes:
                    self.process_vote(vote, bill, member_ids)

                    #some documents/versions are hiding in votes.
                    #deal with them here.

                    if "AttachmentPath" in vote:
                        
                        try:
                            doc_type = vote["DocumentType"]
                        except KeyError:
                            doc_type = "Other"

                        doc_name = vote["ReadingDescription"]
                        for a in vote["AttachmentPath"]:
                            doc = a["Name"]
                            rel_path = a["RelativePath"]
                            doc_url = base_url+"Download/"+rel_path+"/"+doc 
                            if doc_type.lower() in ["enrollment","engrossment"]:
                                if not doc_url in bill_versions:
                                    bill_versions.append(doc_url)
                                    bill.add_version(doc_name,doc_url,mimetype="application/pdf")
                            else:
                                bill.add_document(doc_name,doc_url,mimetype="application/pdf")

                #deal with committee votes
                if "ComiteeMarkup" in bill_info: #their typo, not mine
                    committee_info = bill_info["ComiteeMarkup"]
                    if len(committee_info) > 0:
                        for committee_action in committee_info:
                            self.process_committee_vote(committee_action,bill)
                        if "AttachmentPath" in committee_info:
                            for a in committee_info["AttachmentPath"]:
                                doc_type = a["Type"]
                                doc_name = a["Name"]
                                rel_path = a["RelativePath"]
                                doc_url = base_url+"Download/"+rel_path+"/"+doc_name 
                                bill.add_document(doc_type,doc_url,mimetype="application/pdf")



                #don't know if it makes sense to pass these extra arguments
                #but these urls are totally worthless without them
                bill.add_source(url,headers=headers,json_payload=param_json)
                bill.add_source(bill_url,headers=headers,json_payload=json.dumps(bill_params))
                bill.add_source(base_url+"Legislation/"+bill_id)
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

        date = datetime.datetime.strptime(vote["DateOfVote"].split()[0],"%Y/%m/%d")

        leg_votes = vote["MappedJASON"] #their typo, not mine
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
                t = "amendment:passed"
        elif result in ["Tabled","Postponed"]:
                t = "other" #we don't really have a thing for postponed bills
        elif "first reading" in motion.lower():
            t = "bill:reading:1"
        elif "second reading" in motion.lower():
            t = "bill:reading:2"
        elif "third reading" in motion.lower():
            t = "bill:reading:3"
        elif "final reading" in motion.lower():
            t = "bill:reading:3"
        else:
            t = "other"
        
        bill.add_action("council",
                        motion,
                        date,
                        type=t)

        if "amendment" in t:
            vote["type"] = "amendment"
        elif "reading" in t:
            vote["type"] = t.replace("bill:","")
        bill.add_vote(v)

        

    def process_committee_vote(self,committee_action,bill):
        try:
            date = committee_action["ActionDate"]
            vote_info = committee_action["Vote"]

        except KeyError:
            self.logger.warning("Committee vote has no data. Skipping.")
            return
        date = datetime.datetime.strptime(date.split()[0],"%Y/%m/%d")

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

