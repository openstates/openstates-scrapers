from datetime import datetime
import re

import lxml.html

from openstates.utils import LXMLMixin
from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import scrapelib
import actions


class DEBillScraper(BillScraper, LXMLMixin):
 
    jurisdiction = 'de'

    categorizer = actions.Categorizer()


    def separate_names(self,text):
        text = text.replace("&nbsp","")
        names = re.split("[,;&]",text)
        bad_things_in_names = ["Sen.","Sens.","Rep.","Reps."]
        for name in names:
            for b in bad_things_in_names:
                name = name.replace(b,"")  
            if name.strip():
                yield name.strip()

    def deal_with_action(self,bill,action):
        if "senate" in action.lower():
            actor = "upper"
        elif "house" in action.lower():
            actor = "lower"
        elif "governor" in action.lower():
            actor = "governor"
        else:
            self.logger.warning("Could not find actor for action '{}'".format(action))
            return



    def scrape_bill(self,link,chamber,session):

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



        base_url = "http://legis.delaware.gov"
        text_base_url = "http://legis.delaware.gov/LIS/lis{session}.nsf/vwLegislation/{bill_id}/$file/legis.html?open"
        page = self.lxmlize(link)
        bill_id = page.xpath(".//div[@align='center']")
        try:
            bill_id = bill_id[0].text_content().strip()
        except IndexError:
            self.logger.warning("Can't find bill number, skipping")
            return

        #some bill_ids include relevant amendments
        #in the form "SB 10 w/SA1", so we fix it here
        bill_id = bill_id.split("w/")[0]
        bill_id = bill_id.split("(")[0]
        
        leg_type = None
        for long_name, short_name in legislation_types.items():
            if long_name in bill_id:
                leg_type = short_name
                bill_num = bill_id.replace(long_name,"").strip()
                break
        if leg_type:
            bill_id = leg_type + " " + bill_num
        elif "for" in bill_id:
            bill_id = bill_id.split("for")[1]
        else:
            self.logger.warning("Unknown bill type for {}".format(bill_id))
            return

        #each row is in its own table
        #there are no classes/ids or anything, so we're going to loop
        #through the individual tables and look for keywords
        #in the first td to tell us what we're looking at
        tables = page.xpath(".//table")
        bill_documents = {}
        action_list = []
        sub_link = None
        for table in tables:
            tds = table.xpath(".//td")
            if len(tds) == 0:
                #some kind of empty table for formatting reasons
                continue
            title_text = tds[0].text_content().strip().lower()

            if "primary sponsor" in title_text:
                pri_sponsor_text = tds[1].text_content()
                primary_sponsors = self.separate_names(pri_sponsor_text)
                #sometimes additional sponsors are in a 3rd td
                #other times the 3rd td contains a blank image
                addl_sponsors = []
                add_spons_text = tds[2].text_content().strip()
                if add_spons_text:
                    add_spons_text = add_spons_text.replace("Additional Sponsor(s):","")
                    addl_sponsors = self.separate_names(add_spons_text)

            if "co-sponsor" in title_text:
                cosponsor_text = tds[1].text_content()
                if "none" in cosponsor_text.lower():
                    cosponsors = []
                    continue
                cosponsors = self.separate_names(cosponsor_text)

            if "long title" in title_text:
                bill_title = tds[1].text_content().strip()

            if "amendment" in title_text:
                amendments = tds[1].xpath("./a/text")
                for a in amendments:
                    amm_text = "Amendment {}".format(a.strip())
                    amm_link = base_url.format(session=session,
                                                bill_id = "+".join(a.split()))
                    bill_documents[amm_text] = amm_link

            if "engrossed version" in title_text:
                if tds[1].text_content().strip():
                    engrossment_base = "http://legis.delaware.gov/LIS/lis{session}.nsf/EngrossmentsforLookup/{bill_id}/$file/Engross.html?open"
                    engrossment_link = engrossment_base.format(session=session,
                                        bill_id = "+".join(bill_id.split()))
                    bill_documents["Engrossed Version"] = engrossment_link

            if "substituted" in title_text:
                content = tds[1].text_content().strip()
                if ("Substitute" in content and
                    not "Original" in content):
                    sub_link = tds[1].xpath(".//a/@href")[0]

            if "committee" in title_text:
                pass
                #skipping fiscal notes for now, they are really ugly
                #but leaving in as a placeholder so we can remember to
                #do this someday, if we feel like it

            if "committee" in title_text:
                pass
                #waiting on DE to explain what a vote of "on its merits"
                #means, might do something here if that happens
                #otherwise this will be added as an action.

            if "voting" in title_text:
                pass
                #todo: votes

            if "actions history" in title_text:
                action_list = tds[1].text_content().split("\n")


        if sub_link:
            bill = self.scrape_bill(sub_link,chamber,session)
            bill.add_title(bill_id)

        else:
            bill = Bill(session,chamber,bill_id,bill_title)

            for s in primary_sponsors:
                bill.add_sponsor("primary",s)

            for s in addl_sponsors:
                #it is not totally clear whether "additional sponsors"
                #are co or primary but primary is my best guess
                #based on the bill text, bc they're on the first
                #line with the primary sponsor
                bill.add_sponsor("primary",s)

            for s in cosponsors:
                bill.add_sponsor("cosponsor",s)

        text_base_url = "http://legis.delaware.gov/LIS/lis{session}.nsf/vwLegislation/{bill_id}/$file/legis.html?open"
        #it is totally unclear which version of the bill is referred to here
        #so I'm just calling it "bill text"
        version_url = text_base_url.format(session=session,
                                        bill_id=bill_id.replace(" ","+"))
        bill.add_version("Bill text",version_url,mimetype="text/html")

        for name, doc_link in bill_documents.items():
            if "Engrossment" in name:
                bill.add_version(name,doc_link,mimetype="text/html")
            else:
                bill.add_document(name,doc_link,mimetype="text/html")

        for a in action_list:
            if a.strip():
                date, action = a.split('-', 1)
                try:
                    date = datetime.strptime(date.strip(), '%b %d, %Y')
                except ValueError:
                    date = datetime.strptime(date.strip(), '%B %d, %Y') # XXX: ugh.
                action = action.strip()
                actor = actions.get_actor(action, bill['chamber'])
                attrs = dict(actor=actor, action=action, date=date)
                attrs.update(**self.categorizer.categorize(action))
                bill.add_action(**attrs)




        bill.add_source(link)

        return bill

                




    def scrape(self,chamber,session):
        bill_codes = {"lower":[1,2,3,4],"upper":[5,6,7,8]}
        base_url = "http://legis.delaware.gov/LIS/lis{session}.nsf/ByAll?OpenForm&Start=1&Count={count}&Expand={bill_type}&Seq=1"
        for bill_code in bill_codes[chamber]:
            page = self.lxmlize(base_url.format(session=session,
                                            bill_type=bill_code,
                                            count=1000)) #1000 shld be enough

            #there are not a lot of attributes to hold on to
            #this is the best I could come up with
            tables = page.xpath(".//table")
            good_table = None
            for table in tables:
                th = table.xpath(".//tr/th") 
                if len(th) > 0 and th[0].text_content().strip() == "Type":
                    good_table = table
                    break

            assert good_table is not None, "Could not find a table of bills."

            for tr in good_table.xpath(".//tr"):
                if len(tr.xpath("./td")) < 3:
                    #this is some kind of header row for a bill type
                    continue
                link_td = tr.xpath("./td")[1]
                link = link_td.xpath(".//a/@href")[0]

                bill = self.scrape_bill(link,chamber,session)
                if bill:
                    self.save_bill(bill)





