import re
import datetime
import lxml.html
import json

import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class DCBillScraper(BillScraper):
    jurisdiction = 'dc'

    #TODO: 1) sources
        #2) poke around for other kinds of actions (incl congress)
        #3) poke around for other kinds of documents
        #4) figure out how to deal with "deemed approved" etc statuses
        #5) probably a bunch of other stuff

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


        base_url = "http://lims.dccouncil.us/" #nothing is actual links. we'll have to concatenate to get doc paths (documents are hiding in thrice-stringified json. eek.)
        headers = {"Content-Type":"application/json"}
        url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicAdvancedSearch"
        bill_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicData"
        params = {"request":{"sEcho":2,"iColumns":4,"sColumns":"","iDisplayStart":10,"iDisplayLength":10,"mDataProp_0":"ShortTitle","mDataProp_1":"Title","mDataProp_2":"LegislationCategories","mDataProp_3":"Modified","iSortCol_0":0,"sSortDir_0":"asc","iSortingCols":0,"bSortable_0":"true","bSortable_1":"true","bSortable_2":"true","bSortable_3":"true"},"criteria":{"Keyword":"","Category":"","SubCategoryId":"","RequestOf":"","CouncilPeriod":str(session),"Introducer":"","CoSponsor":"","ComitteeReferral":"","CommitteeReferralComments":"","StartDate":"","EndDate":"","QueryLimit":100,"FilterType":"","Phases":"","LegislationStatus":"0","IncludeDocumentSearch":"false"}}
        param_json = json.dumps(params)
        response = self.post(url,headers=headers,data=param_json)
        #the response is a terrible string-of-nested-json-strings. Yuck.
        response = self.decode_json(response.json()["d"])
        num_records = response["iTotalRecords"]
        data = response["aaData"]

        for bill in data:
            bill_id = bill["Title"]
            bill_params = {"legislationId":bill_id}
            bill_info = self.post(bill_url,headers=headers,data=json.dumps(bill_params))
            bill_info = self.decode_json(bill_info.json()["d"])["data"]
            
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
                if "TransmittedDate" in mayor:
                    transmitted_date = mayor["TransmittedDate"].split(" ")[0]
                    transmitted_date = datetime.datetime.strptime(transmitted_date,"%Y/%m/%d")

                    bill.add_action("mayor",
                                "transmitted to mayor",
                                transmitted_date)

                if 'EnactedDate' in mayor:
                    enacted_date = mayor["EnactedDate"].split(" ")[0]
                    enacted_date = datetime.datetime.strptime(enacted_date,"%Y/%m/%d")

                    bill.add_action("mayor",
                                    "enacted",
                                    enacted_date)


            #deal with committee actions
            reading_date = legislation_info["DateRead"].split(" ")[0] #time is always 0
            reading_date = datetime.datetime.strptime(reading_date,"%Y/%m/%d")
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
                                reading_date,
                                committees=committees)

            if "CommitteeReferralComments" in legislation_info:
                committees = []
                for committee in legislation_info["CommitteeReferralComments"]:
                    committees.append(committee["Name"])
                bill.add_action("committee",
                                "retained by council with comments from committees",
                                reading_date,
                                committees=committees)

            

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

            #self.save_bill(bill)
    
    def get_member_ids(self):
        member_dict = {} #three levels: from session to member_id to name
        search_data_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicSearchData"
        response = self.post(search_data_url,headers={"Content-Type":"application/json"})
        member_data = self.decode_json(response.json()['d'])["Members"]
        for session_id, members in member_data.items():
            member_dict[session_id] = {}
            for member in members:
                member_id = member["ID"]
                member_name = member["MemberName"]
                member_dict[session_id][member_id] = member_name

        return member_dict


    def process_vote(self, vote, bill, member_ids):
        result = vote["VoteResult"]
        motion = vote["ReadingDescription"]

        try:
            status = {"approved":True,"disapproved":False}[result.strip().lower()]
        except KeyError:
            self.logger.warning("Unexpected vote result {result}, skipping vote.".format(result=result))
            return

        date = datetime.datetime.strptime(vote["DateOfVote"].split()[0],"%Y/%m/%d")

        leg_votes = vote["MappedJASON"] #their typo, not mine
        v = Vote('upper',date,motion,status,0,0,0,
                yes_votes=[],no_votes=[],other_votes=[])
        for leg_vote in leg_votes:
            mem_name = member_ids[leg_vote["MemberId"]]
            if leg_vote["Vote"] == "1":
                v['yes_count'] += 1
                v['yes_votes'].append(mem_name)
            elif leg_vote["Vote"] == "0":
                v['no_count'] += 1
                v['no_votes'].append(mem_name)
            else:
                v['other_count'] += 1
                v['other_votes'].append(mem_name)



        bill.add_vote(v)


        



