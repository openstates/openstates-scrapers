from fiftystates.scrape.ms import metadata
from fiftystates.scrape.ms.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote
from fiftystates.scrape.utils import convert_pdf
from datetime import datetime
import lxml.etree
import re

def _combine_lines(lines):
    newlines = []
    lastline = '.'
    for line in lines:
        if lastline and lastline[-1] in '.,:' and not line.startswith('('):
            newlines.append(line)
            lastline = line
        else:
            lastline = newlines[-1] = newlines[-1] + ' ' + line
    return newlines

class MSBillScraper(BillScraper):
    state = 'ms'

    _action_types = (
        ('Died in Committee', 'committee:failed'),
        ('Enrolled Bill Signed', 'other'),
        ('Immediate Release', 'other'),
        ('Passed', 'bill:passed'),
        ('Adopted', 'bill:passed'),
        ('Amended', 'amendment:passed'),
        ('Failed', 'bill:failed'),
        ('Committee Substitute Adopted', 'bill:substituted'),
        ('Amendment Failed', 'amendment:failed'),
        ('Amendment Withdrawn', 'amendment:withdrawn'),
        ('Referred To', 'committee:referred'),
        ('Rereferred To', 'committee:referred'),
        ('Transmitted To', 'bill:introduced'),
        ('Approved by Governor', 'governor:signed'),
        ('Vetoed', 'governor:vetoed'),
        ('Partially Vetoed', 'governor:vetoed:line-item'),
        ('Title Suff Do', 'committee:passed'),
        ('Read the Third Time', 'bill:reading:3'),
    )

    def scrape(self, chamber, session):
        self.save_errors=False
        if int(session[0:4]) < 2008:
            raise NoDataForPeriod(session)
        self.scrape_bills(chamber, session)

    def scrape_bills(self, chamber_to_scrape, session):
        url = 'http://billstatus.ls.state.ms.us/%s/pdf/all_measures/allmsrs.xml' % session

        with self.urlopen(url) as bill_dir_page:
            root = lxml.etree.fromstring(bill_dir_page, lxml.etree.HTMLParser())
            for mr in root.xpath('//lastaction/msrgroup'):
                bill_id = mr.xpath('string(measure)').replace(" ", "")
                if bill_id[0] == "S":
                    chamber = "upper"
                else:
                    chamber = "lower"

                bill_type = {'B':'bill', 'C': 'concurrent resolution',
                             'R': 'resolution', 'N': 'nomination'}[bill_id[1]]

                # just skip past bills that are of the wrong chamber
                if chamber != chamber_to_scrape:
                    continue

                link = mr.xpath('string(actionlink)').replace("..", "")
                main_doc = mr.xpath('string(measurelink)').replace("../../../", "")
                main_doc_url = 'http://billstatus.ls.state.ms.us/%s' % main_doc
                bill_details_url = 'http://billstatus.ls.state.ms.us/%s/pdf/%s' % (session, link)
                with self.urlopen(bill_details_url) as details_page:
                    details_page = details_page.decode('latin1').encode('utf8', 'ignore')
                    details_root = lxml.etree.fromstring(details_page, lxml.etree.HTMLParser())
                    title = details_root.xpath('string(//shorttitle)')
                    longtitle = details_root.xpath('string(//longtitle)')

                    bill = Bill(session, chamber, bill_id, title,
                                type=bill_type, longtitle=longtitle)

                    #sponsors
                    main_sponsor = details_root.xpath('string(//p_name)').split()
                    if main_sponsor:
                        main_sponsor = main_sponsor[0]
                        main_sponsor_link = details_root.xpath('string(//p_link)').replace(" ", "_")
                        main_sponsor_url =  'http://billstatus.ls.state.ms.us/%s/pdf/House_authors/%s.xml' % (session, main_sponsor_link)
                        type = "primary"
                        bill.add_sponsor(type, main_sponsor, main_sponsor_url = main_sponsor_url)
                    for author in details_root.xpath('//authors/additional'):
                        leg = author.xpath('string(co_name)').replace(" ", "_")
                        leg_url = 'http://billstatus.ls.state.ms.us/%s/pdf/House_authors/%s.xml' % (session, leg)
                        type = "cosponsor"
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

                        atype = 'other'
                        for prefix, prefix_type in self._action_types:
                            if action.startswith(prefix):
                                atype = prefix_type
                                break

                        bill.add_action(actor, action, date, type=atype,
                                        action_num=action_num)

                        if act_vote:
                            vote_url = 'http://billstatus.ls.state.ms.us%s' % act_vote
                            vote = self.scrape_votes(vote_url, action, date, actor)
                            bill.add_vote(vote)
                            bill.add_source(vote_url)

                    bill.add_source(bill_details_url)
                    self.save_bill(bill)

    _vote_mapping = {
        'Passed': ('Passage', True),
        'Adopted': ('Passage', True),
        'Failed': ('Passage', False),
        'Passed As Amended': ('Passage as Amended', True),
        'Adopted As Amended': ('Passage as Amended', True),
        'Appointment Confirmed': ('Appointment Confirmation', True),
        'Committee Substitute Adopted': ('Adopt Committee Substitute', True),
        'Conference Report Adopted': ('Adopt Conference Report', True),
        'Conference Report Failed': ('Adopt Conference Report', False),
        'Motion to Reconsider Tabled': ('Table Motion to Reconsider', True),
        'Motion to Recnsdr Tabled Lost': ('Table Motion to Reconsider', False),
        'Veto Overridden': ('Override Veto', True),
        'Veto Sustained': ('Override Veto', False),
        'Concurred in Amend From House': ('Concurrence in Amendment From House', True),
        'Concurred in Amend From Senate': ('Concurrence in Amendment From Senate', True),
        'Decline to Concur/Invite Conf': ('Decline to Concur', True),
        'Decline Concur/Inv Conf Lost': ('Decline to Concur', False),
        'Failed to Suspend Rules': ('Motion to Suspend Rules', False),
        'Motion to Recommit Lost': ('Motion to Recommit', True),
        'Reconsidered': ('Reconsideration', True),
        'Motion to Concur Failed': ('Motion to Concur', False),
        'Recommitted to Committee': ('Recommit to Committee', True),
    }

    def scrape_votes(self, url, motion, date, chamber):
        vote_pdf, resp = self.urlretrieve(url)
        text = convert_pdf(vote_pdf, 'text')

        if motion in self._vote_mapping:
            motion, passed = self._vote_mapping[motion]
        else:
            passed = False
            self.warning('unknown vote type: ' + motion)

        # process PDF text

        yes_votes = []
        no_votes = []
        other_votes = []

        # point at array to add names to
        cur_array = None

        precursors = (
            ('Yeas--', yes_votes),
            ('Nays--', no_votes),
            ('Absent or those not voting--', other_votes),
            ('Absent and those not voting--', other_votes),
            ('Voting Present--', other_votes),
            ('Present--', other_votes),
            ('DISCLAIMER', None),
        )

        # split lines on newline, recombine lines that don't end in punctuation
        lines = _combine_lines(text.split('\n'))

        for line in lines:

            # check if the line starts with a precursor, switch to that array
            for pc, arr in precursors:
                if pc in line:
                    cur_array = arr
                    line = line.replace(pc, '')

            # split names
            for name in line.split(','):
                name = name.strip()

                # None or a Total indicate the end of a section
                if 'None.' in name:
                    cur_array = None
                match = re.match(r'(.+?)\. Total--.*', name)
                if match:
                    cur_array.append(match.groups()[0])
                    cur_array = None

                # append name if it looks ok
                if cur_array is not None and name and 'Total--' not in name:
                    # strip trailing .
                    if name[-1] == '.':
                        name = name[:-1]
                    cur_array.append(name)

        # return vote object
        yes_count = len(yes_votes)
        no_count = len(no_votes)
        other_count = len(other_votes)
        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count)
        vote['yes_votes'] = yes_votes
        vote['no_votes'] = no_votes
        vote['other_votes'] = other_votes
        return vote
