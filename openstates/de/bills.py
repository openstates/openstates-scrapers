from datetime import datetime
import re
import lxml.html
import requests
import actions
from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin


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

    def find_vote(self,tds,vote_documents,extra=""):
        vote_info = tds[1].xpath('./a')
        for v in vote_info:
            prev = v.getprevious()
            vote_name = extra+prev.text_content().strip()
            vote_documents[vote_name] = v.attrib["href"]

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
        try:
            page = self.lxmlize(link, True)
        except requests.exceptions.HTTPError:
            self.logger.warning('404. Apparently the bill hasn\'t been posted')
            return
        nominee = self.get_node(page, './/div[@id="page_header"]/text()')
        if nominee is not None and nominee.strip().lower() == "nominee information":
            self.logger.info("Nominee, skipping")
            return

        bill_id = self.get_node(page, './/div[@align="center" or @style="text-align:center"]')
        try:
            bill_id = bill_id.text_content().strip()
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

        bill_id = bill_id.replace('&nbsp',"")
        bill_id = bill_id.strip()

        #each row is in its own table
        #there are no classes/ids or anything, so we're going to loop
        #through the individual tables and look for keywords
        #in the first td to tell us what we're looking at
        tables = self.get_nodes(page, './/div[@id="page_content"]/table')

        bill_title = None
        primary_sponsors = []
        cosponsors = []
        bill_url = None
        bill_documents = {}
        action_list = []
        vote_documents = {}
        sub_link = None
        bill_text_avail = False

        if tables is None or not tables:
            self.logger.warning('First xpath didn\'t work.')
            tables = self.get_nodes(page, './/table[@style="width:837.0px"]/tr')

        for table in tables:
            tds = table.xpath('.//td')
            if len(tds) == 0:
                #some kind of empty table for formatting reasons
                continue
            title_text = tds[0].text_content().strip().lower()

            if title_text.startswith('primary sponsor'):
                pri_sponsor_text = tds[1].text_content()
                primary_sponsors = self.separate_names(pri_sponsor_text)
                #sometimes additional sponsors are in a 3rd td
                #other times the 3rd td contains a blank image
                addl_sponsors = []
                add_spons_text = tds[2].text_content().strip()
                if add_spons_text:
                    add_spons_text = add_spons_text.replace("Additional Sponsor(s):","")
                    if not "on behalf of all representatives" in add_spons_text.lower():
                        addl_sponsors = self.separate_names(add_spons_text)

            elif title_text.startswith('co-sponsor'):
                cosponsor_text = tds[1].text_content()
                if "none..." in cosponsor_text.lower():
                    cosponsors = []
                    continue
                cosponsors = self.separate_names(cosponsor_text)

            elif title_text.startswith('long title'):
                bill_title = tds[1].text_content().strip()

            elif title_text.startswith('amendment'):
                amendments = tds[1].xpath('.//a')
                for a in amendments:
                    amm = a.text
                    amm_text = "Amendment".format(amm.strip())
                    amm_slg = "+".join(amm.split())
                    amm_link = text_base_url.format(session=session,
                                                bill_id=amm_slg)
                    bill_documents[amm_text] = amm_link
                    amm_page = self.lxmlize(a.attrib["href"])
                    for tr in amm_page.xpath('//tr'):
                        tds = tr.xpath("./td")
                        if len(tds) > 1:
                            if "voting" in tds[0].text_content().lower():
                                self.find_vote(tds,vote_documents,"Amendment: ")

            elif title_text.startswith('engrossed version'):
                if tds[1].text_content().strip():
                    engrossment_base = "http://legis.delaware.gov/LIS/lis{session}.nsf/EngrossmentsforLookup/{bill_id}/$file/Engross.html?open"
                    engrossment_link = engrossment_base.format(session=session,
                                        bill_id = "+".join(bill_id.split()))
                    if bill_url not in bill_documents.values():
                        bill_documents["Engrossed Version"] = engrossment_link

            elif title_text.startswith('substituted'):
                content = tds[1].text_content().strip()
                if ("Substitute" in content and
                    not "Original" in content):
                    sub_link = tds[1].xpath(".//a/@href")[0]

            elif ("full text" in title_text
                and ("(" not in title_text
                or "html" in title_text)):
                    if tds[1].text_content().strip():
                        #it is totally unclear which version of the bill is referred to here
                        #so I'm just calling it "bill text"
                        bill_url = text_base_url.format(
                                        session=session,
                                        bill_id=bill_id.replace(" ","+"))
                        if bill_url not in bill_documents.values():
                            bill_documents["Bill Text"] = bill_url

            elif title_text.startswith('fiscal notes'):
                pass
                #skipping fiscal notes for now, they are really ugly
                #but leaving in as a placeholder so we can remember to
                #do this someday, if we feel like it

            elif title_text.startswith('committee reports'):
                pass
                #the committee reports let a legislator
                #comment on a bill. They can comment as
                #"favorable","unfavorable" or "on its merits"
                #but these are NOT votes (per conversation w
                #seceretary of the DE senate 3/16/15). The bill is
                #considered if the majority sign it, which will
                #appear in the bill's action history as being
                #reported out of committee

            elif title_text.startswith('voting'):
                self.find_vote(tds,vote_documents)
            elif title_text.startswith('actions history'):
                action_list = tds[1].text_content().split("\n")

        sub_versions = []
        use_sub = False
        if sub_link:
            bill = self.scrape_bill(sub_link,chamber,session)
            if bill:
                sub_versions = [v["url"] for v in bill["versions"]]
                bill.add_title(bill_id)
                use_sub = True

        if not use_sub:
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

        for name, doc_link in bill_documents.items():
            if "Engrossment" in name or "Bill Text" in name:
                if doc_link not in sub_versions:
                    bill.add_version(name,doc_link,mimetype="text/html")
            else:
                pass
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
                attrs["action"] = " ".join(attrs["action"].split())
                bill.add_action(**attrs)

        for name, doc in vote_documents.items():
            vote_chamber = "lower" if "house" in name.lower() else "upper"
            try:
                self.head(doc)
            except requests.exceptions.HTTPError:
                self.logger.warning("could not access vote document")
                continue

            vote_page = self.lxmlize(doc)

            try:
                vote_info = vote_page.xpath('.//div[@id="page_content"]/p')[-1]
                vote_tds = vote_page.xpath(".//table//td")
            except IndexError:
                vote_info = vote_page.xpath('.//form[1]')[0]
                vote_tds = vote_page.xpath('.//table[@border="0"]//td')

            yes_votes = []
            no_votes = []
            other_votes = []

            lines = vote_info.text_content().split("\n")
            lines = filter(None, lines)

            for line in lines:
                if line.strip().startswith("Date"):
                    date_str = " ".join(line.split()[1:4])
                    date = datetime.strptime(date_str,"%m/%d/%Y %I:%M %p")
                    passage_status = line.strip().split()[-1]

                    #we've never seen a vote with anything but "passed"
                    #so throw an error otherwise so we can figure it out
                    passed_statuses = ["Passed"]
                    failed_statuses = ["Defeated", "Rescinded"]
                    if passage_status not in passed_statuses+failed_statuses:
                        raise AssertionError("Unknown passage state {}".format(passage_status))
                    passed = passage_status in passed_statuses

                if line.strip().startswith("Vote Type"):
                    if "voice" in line.lower():
                        voice_vote = True
                    else:
                        voice_vote = False
                        yes_count = int(re.findall("Yes: (\d+)",line)[0])
                        no_count = int(re.findall("No: (\d+)",line)[0])
                        other_count = int(re.findall("Not Voting: (\d+)",line)[0])
                        other_count += int(re.findall("Absent: (\d+)",line)[0])

                        person_seen = False

                        for td in vote_tds:
                            if person_seen:
                                person_vote = td.text_content().strip()
                                if person_vote == "Y":
                                    yes_votes.append(person)
                                elif person_vote == "N":
                                    no_votes.append(person)
                                elif person_vote in ["NV","A","X","C"]:
                                    other_votes.append(person)
                                else:
                                    raise AssertionError("Unknown vote '{}'".format(person_vote))
                                person_seen = False
                            else:
                                person = td.text_content().strip()
                                if person:
                                    person_seen = True

            if voice_vote:
                vote = Vote(vote_chamber,date,"passage",passed,0,0,0)
            else:
                vote = Vote(vote_chamber,date,"passage",
                            passed,yes_count,no_count,other_count,
                            yes_votes=[],
                            no_votes=[],
                            other_votes=[])

                vote["yes_votes"] = yes_votes
                vote["no_votes"] = no_votes
                vote["other_votes"] = other_votes

            if (passed
                and vote["yes_count"] <= vote["no_count"]
                and not voice_vote):
                    raise AssertionError("Vote passed with more N than Y votes?")

            if not passed and vote["yes_count"] > vote["no_count"]:
                self.logger.warning("Vote did not pass but had a majority \
                        probably worth checking")

            if "Amendment" in name:
                vote["type"] = "amendment"
            else:
                vote["type"] = "passage"
            vote.add_source(doc)
            bill.add_vote(vote)

        bill.add_source(link)

        return bill

    def scrape(self,chamber,session):
        bill_codes = {"lower":[1,2,3,4],"upper":[5,6,7,8]}
        base_url = "http://legis.delaware.gov/LIS/lis{session}.nsf/ByAll?OpenForm&Start=1&Count={count}&Expand={bill_type}&Seq=1"
        for bill_code in bill_codes[chamber]:
            page = self.lxmlize(base_url.format(session=session,
                                            bill_type=bill_code,
                                            count=1000))
                                            #1000 is higher than the highest
                                            #TOTAL # of bills we've ever seen 

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
