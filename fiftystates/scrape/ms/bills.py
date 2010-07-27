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
                    main_sponsor = details_root.xpath('string(//p_name)')
                    main_sponsor_link = details_root.xpath('string(//p_link)').replace(" ", "_")
                    main_sponsor_url =  'http://billstatus.ls.state.ms.us/2010/pdf/House_authors/%s.xml' % main_sponsor_link
                    type = "Primary sponsor"
                    bill.add_sponsor(type, main_sponsor, main_sponsor_url = main_sponsor_url)
                    for author in details_root.xpath('//authors/additional'):
                        leg = author.xpath('string(co_name)').replace(" ", "_")
                        leg_url = 'http://billstatus.ls.state.ms.us/2010/pdf/House_authors/%s.xml' % leg
                        type = "additional sponsor"
                        bill.add_sponsor(type, leg, leg_url=leg_url)

                    #Actions
                    for action in details_root.xpath('//history/action'):
                        action_num  = action.xpath('string(act_number)')
                        action_desc = action.xpath('string(act_desc)')
                        act_vote = action.xpath('string(act_vote)').replace("../../../..", "")
                        date = action_desc.split()[0] + "/" + session[0:4]
                        date = datetime.strptime(date, "%m/%d/%Y")
                        actor = action_desc.split()[1][1]
                        if actor == "H":
                            actor = "House of Representatives"
                        else:
                            actor = "Senate"
                        action = action_desc[10: len(action_desc)]
                        bill.add_action(actor, action, date, action_num=action_num)                        

                        vote_url = 'http://billstatus.ls.state.ms.us%s' % act_vote
                        if vote_url != "http://billstatus.ls.state.ms.us":
                            vote =self.scrape_votes(vote_url, action, date, chamber)
                            bill.add_vote(vote)
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
        passed = text.find("passed") != -1
        split_text = text.split(",")
        yea_mark = split_text.index("Yeas") + 1
        end_mark = split_text.index("DISCLAIMER")
        nays, other = False, False
        yes_votes = []
        no_votes = []
        other_votes = []
        for num in range(yea_mark, end_mark):
            name = split_text[num].replace(" ", "")
            name = name.replace("\n", "")
            if nays == False and other == False and name != "Total" and name != "Nays" and not re.match("\d{1,2}\.", name) and len(name) > 1:
                yes_votes.append(name)
            elif nays == True and other == False and name != "Total" and name != "Absentorthosenotvoting" and not re.match("\d{1,2}\.", name) and len(name) > 1:
                 no_votes.append(name)
            elif nays == False and other == True and name != "Total" and not re.match("\d{1,2}\.", name) and len(name) > 1:
                other_votes.append(name)
            else:
                if name == "Nays":
                    nays = True
                if name == "Absentorthosenotvoting":
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
