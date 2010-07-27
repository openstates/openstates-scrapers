from fiftystates.scrape.me import metadata
from fiftystates.scrape.me.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote
from datetime import datetime
import lxml.etree

class MEBillScraper(BillScraper):
    state = 'me'

    def scrape(self, chamber, session):
        session = int(session)
        if session < 121:
            raise NoDataForPeriod(session)
        session_id = (int(session) - 124) + 8

        if str(session)[-1] == "1":
            session_abr = str(session) + "st"
        elif str(session)[-1] == "2":
            session_abr = str(session) + "nd"
        elif str(session)[-1] == "3":
            session_abr = str(session) + "rd"
        else:
            session_abr = str(session) + "th"
        
        self.scrape_bill(session, session_id, session_abr)

    def scrape_bill(self, session, session_id, session_abr):
        main_directory_url = 'http://www.mainelegislature.org/legis/bills/bills_%s/billtexts/' % session_abr

        with self.urlopen(main_directory_url) as main_directory_page:
            root = lxml.etree.fromstring(main_directory_page, lxml.etree.HTMLParser())
            main_dir_links = root.xpath('//tr/td/ul/li//@href')
            for link in main_dir_links:
                dir_url = 'http://www.mainelegislature.org/legis/bills/bills_%s/billtexts/%s' % (session_abr, link)
                with self.urlopen(dir_url) as dir_page:
                    root = lxml.etree.fromstring(dir_page, lxml.etree.HTMLParser())
                    count = 1
                    for mr in root.xpath('/html/body/dl/dt/big/a[1]'):
                        ld = mr.xpath('string()')
                        ld = ld.replace(",", "")
                        ld = ld.split()[1]
                        bill_id_path = 'string(/html/body/dl/dt[%s]/big/a[2])' % count
                        bill_id = root.xpath(bill_id_path)
                        title_path = 'string(/html/body/dl/dd[%s]/font)' % count
                        title = root.xpath(title_path)
                        count = count + 1
                        self.scrape_bill_info(session, ld, session_id, bill_id, title)

    def scrape_bill_info(self, session, ld, session_id, bill_id, title):
        bill_info_url  = 'http://www.mainelegislature.org/LawMakerWeb/summary.asp?LD=%s&SessionID=%s' % (ld, session_id)
        with self.urlopen(bill_info_url) as bill_sum_page:
            root = lxml.etree.fromstring(bill_sum_page, lxml.etree.HTMLParser())
            sponsor = root.xpath('string(//tr[3]/td[1]/b[1])')
            if bill_id[0] == "S":
                chamber = "upper"
            else:
                chamber = "lower"
            bill = Bill(str(session), chamber, bill_id, title)
            bill.add_source(bill_info_url)

            #Actions
            actions_url_addon = root.xpath('string(//table/tr[3]/td/a/@href)')
            actions_url = 'http://www.mainelegislature.org/LawMakerWeb/%s' % actions_url_addon
            bill.add_source(actions_url)
            with self.urlopen(actions_url) as actions_page:
                root2 = lxml.etree.fromstring(actions_page, lxml.etree.HTMLParser())
                count = 2
                for mr in root2.xpath("//td[2]/table[2]/tr[position() > 1]/td[1]"):
                    date = mr.xpath('string()')
                    date = datetime.strptime(date, "%m/%d/%Y")
                    actor_path = "string(//td[2]/table/tr[%s]/td[2])" % count
                    actor = root2.xpath(actor_path)
                    action_path = "string(//td[2]/table/tr[%s]/td[3])" % count
                    action = root2.xpath(action_path)
                    count = count + 1
                    if actor == "House":
                        actor = "lower"
                    else:
                        actor = "upper"
                    bill.add_action(actor, action, date)
            #Votes
            votes_url_addon = root.xpath('string(//table/tr[9]/td/a/@href)')
            votes_url = 'http://www.mainelegislature.org/LawMakerWeb/%s' % votes_url_addon
            bill.add_source(votes_url)
            with self.urlopen(votes_url) as votes_page:
                vote_root = lxml.etree.fromstring(votes_page, lxml.etree.HTMLParser())
                for mr in vote_root.xpath('//table[position() > 1]/tr/td/a'):
                    vote_detail_addon = mr.xpath('string(@href)')
                    vote_detail_url = 'http://www.mainelegislature.org/LawMakerWeb/%s' % vote_detail_addon
                    bill.add_source(vote_detail_url)
                    with self.urlopen(vote_detail_url) as vote_detail_page:
                        detail_root = lxml.etree.fromstring(vote_detail_page, lxml.etree.HTMLParser())
                        date = detail_root.xpath('string(//table[2]//tr[2]/td[3])')
                        try:
                            date = datetime.strptime(date, "%B %d, %Y")
                        except:
                            date = datetime.strptime(date, "%b. %d, %Y")
                        motion = detail_root.xpath('string(//table[2]//tr[3]/td[3])')
                        passed = detail_root.xpath('string(//table[2]//tr[5]/td[3])') == 'PREVAILS'
                        yes_count = detail_root.xpath('string(//table[2]//tr[6]/td[3])')
                        no_count = detail_root.xpath('string(//table[2]//tr[7]/td[3])')
                        absent_count = detail_root.xpath('string(//table[2]//tr[6]/td[3])')
                        excused_count = detail_root.xpath('string(//table[2]//tr[6]/td[3])')
                        other_count = None

                        if votes_url.find('House') != -1:
                            chamber = "lower"
                        else:
                            chamber = "upper"

                        vote = Vote(chamber, date, motion, passed, yes_count, no_count, other_count, absent_count = absent_count, excused_count = excused_count)

                        for member in detail_root.xpath('//table[3]/tr[position() > 1]'):
                            leg = member.xpath('string(td[2])')
                            party = member.xpath('string(td[3])')
                            leg_vote = member.xpath('string(td[4])')

                            if leg_vote == "Y":
                                vote.yes(leg)
                            elif leg_vote == "N":
                                vote.no(leg)
                            else:
                                vote.other(leg)
                        bill.add_vote(vote)
            self.save_bill(bill)
