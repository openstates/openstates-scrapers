from fiftystates.scrape.ms import metadata
from fiftystates.scrape.ms.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote
from fiftystates.scrape.utils import convert_pdf
from datetime import datetime
import lxml.etree
import re

class MSBillScraper(BillScraper):
    state = 'ms'

    def scrape(self, chamber, session):
        self.save_errors=False
        if int(session[0:4]) < 2008:
            raise NoDataForPeriod(session)
        self.scrape_bills(session)

    def scrape_bills(self, session):
        url = 'http://billstatus.ls.state.ms.us/%s/pdf/all_measures/allmsrs.xml' % session

        with self.urlopen(url) as bill_dir_page:
            root = lxml.etree.fromstring(bill_dir_page, lxml.etree.HTMLParser())
            for mr in root.xpath('//lastaction/msrgroup'):
                bill_id = mr.xpath('string(measure)').replace(" ", "")
                if bill_id[0] == "S":
                    chamber = "upper"
                else:
                    chamber = "lower"
                link = mr.xpath('string(actionlink)').replace("..", "")
                main_doc = mr.xpath('string(measurelink)').replace("../../../", "")
                main_doc_url = 'http://billstatus.ls.state.ms.us/%s' % main_doc
                bill_details_url = 'http://billstatus.ls.state.ms.us/%s/pdf/%s' % (session, link)
                with self.urlopen(bill_details_url) as details_page:
                    details_page = details_page.decode('latin1').encode('utf8', 'ignore')
                    details_root = lxml.etree.fromstring(details_page, lxml.etree.HTMLParser())
                    title = details_root.xpath('string(//shorttitle)')
                    longtitle = details_root.xpath('string(//longtitle)')

                    bill = Bill(session, chamber, bill_id, title, longtitle = longtitle)

                    #sponsors
                    main_sponsor = details_root.xpath('string(//p_name)').split()[0]
                    main_sponsor_link = details_root.xpath('string(//p_link)').replace(" ", "_")
                    main_sponsor_url =  'http://billstatus.ls.state.ms.us/%s/pdf/House_authors/%s.xml' % (session, main_sponsor_link)
                    type = "Primary sponsor"
                    bill.add_sponsor(type, main_sponsor, main_sponsor_url = main_sponsor_url)
                    for author in details_root.xpath('//authors/additional'):
                        leg = author.xpath('string(co_name)').replace(" ", "_")
                        leg_url = 'http://billstatus.ls.state.ms.us/%s/pdf/House_authors/%s.xml' % (session, leg)
                        type = "additional sponsor"
                        bill.add_sponsor(type, leg, leg_url=leg_url)


                    #Versions 
                    curr_version = details_root.xpath('string(//current_other)').replace("../../../../", "")
                    curr_version_url = "http://billstatus.ls.state.ms.us/" + curr_version
                    bill.add_version("Current version", curr_version_url)

                    intro_version = details_root.xpath('string(//intro_other)').replace("../../../../", "")
                    intro_version_url = "http://billstatus.ls.state.ms.us/" + intro_version
                    bill.add_version("As Introduced", intro_version_url)

                    comm_version = details_root.xpath('string(//cmtesub_other)').replace("../../../../", "")
                    if comm_version.find("documents") != -1:
                        comm_version_url = "http://billstatus.ls.state.ms.us/" + comm_version
                        bill.add_version("Committee Substitute", comm_version_url)

                    passed_version = details_root.xpath('string(//passed_other)').replace("../../../../", "")
                    if passed_version.find("documents") != -1:
                        passed_version_url = "http://billstatus.ls.state.ms.us/" + passed_version
                        title = "As Passed the " + chamber
                        bill.add_version(title, passed_version_url)

                    asg_version = details_root.xpath('string(//asg_other)').replace("../../../../", "")
                    if asg_version.find("documents") != -1:
                        asg_version_url = "http://billstatus.ls.state.ms.us/" + asg_version
                        bill.add_version("Approved by the Governor", asg_version_url)


                    #Actions
                    for action in details_root.xpath('//history/action'):
                        action_num  = action.xpath('string(act_number)').strip()
                        action_num = int(action_num)
                        act_vote = action.xpath('string(act_vote)').replace("../../../..", "")
                        action_desc = action.xpath('string(act_desc)')
                        date, action_desc = action_desc.split(" ", 1)
                        date = date + "/" + session[0:4]
                        date = datetime.strptime(date, "%m/%d/%Y")

                        if action_desc.startswith("(H)"):
                            actor = "lower"
                            action = action_desc[4:]
                        elif action_desc.startswith("(S)"):
                            actor = "upper"
                            action = action_desc[4:]
                        else:
                            actor = "executive"
                            action = action_desc

                        if action.find("Veto") != -1:
                            version_path = details_root.xpath("string(//veto_other)")
                            version_path = version_path.replace("../../../../", "")
                            version_url = "http://billstatus.ls.state.ms.us/" + version_path
                            bill.add_document("Veto", version_url) 

                        bill.add_action(actor, action, date,
                                        action_num=action_num)

                        vote_url = 'http://billstatus.ls.state.ms.us%s' % act_vote
                        #if vote_url != "http://billstatus.ls.state.ms.us":
                            #vote = self.scrape_votes(vote_url, action, date, actor)
                            #bill.add_vote(vote)
                            #bill.add_source(vote_url)

                    bill.add_source(bill_details_url)
                    self.save_bill(bill)

    def scrape_votes(self, url, motion, date, chamber):
        vote_pdf, resp = self.urlretrieve(url)
        text = convert_pdf(vote_pdf, 'text')
        text = text.replace("Yeas--", ",Yeas, ")
        text = text.replace("Nays--", ",Nays, ")
        text = text.replace("Total--", ",Total, ")
        text = text.replace("DISCLAIMER", ",DISCLAIMER,")
        text = text.replace("--", ",")
        text = text.replace("Absent or those not voting", ",Absentorthosenotvoting,")
        passed = ('passed' in text) or ('concurred' in text)
        split_text = text.split(",")
        yea_mark = split_text.index("Yeas") + 1
        end_mark = split_text.index("DISCLAIMER")
        nays, other = False, False
        yes_votes = []
        no_votes = []
        other_votes = []
        for num in range(yea_mark, end_mark):
            name = split_text[num]
            name = name.replace("\n", "")

            if name.find("(") != -1:
                if len(name.split()) == 2:
                    name = name.split()[0]
                if len(name.split()) == 3:
                    name =  name.split()[0] + " " + name.split()[1]

            if len(name) > 0 and name[0] == " ":
                name = name[1: len(name)]

            if len(name.split()) > 3:
                name = name.replace(" ", "")

            if self.check_name(name, nays, other) == 'yes':
                yes_votes.append(name)
            elif self.check_name(name, nays, other) == 'no':
                no_votes.append(name)
            elif self.check_name(name, nays, other) == 'other':
                other_votes.append(name)
            else:
                if name == "Nays":
                    nays = True
                if name.find("Absent") != -1:
                    nays = False
                    other = True
        yes_count = len(yes_votes)
        no_count = len(no_votes)
        other_count = len(other_votes)
        vote = Vote(chamber, date, motion, passed, yes_count, no_count, other_count)
        vote['yes_votes'] = yes_votes
        vote['no_votes'] = no_votes
        vote['other_votes'] = other_votes
        return vote

    def check_name(self, name, nays, other):
        if nays == False and other == False and name != "Total" and name != "Nays" and not re.match("\d{1,2}\.", name) and len(name) > 1:
            return 'yes'
        elif nays == True and other == False and name != "Total" and name.find("Absentor") == -1 and not re.match("\d{1,2}\.", name) and len(name) > 1 and name.find("whowouldhave") == -1 and name.find("announced") == -1:
            return 'no'
        elif nays == False and other == True and name != "Total" and not re.match("\d{1,2}\.", name) and len(name) > 1 and name.find("whowouldhave") == -1 and name.find("announced") == -1:
            return 'other'
        else:
            return None
