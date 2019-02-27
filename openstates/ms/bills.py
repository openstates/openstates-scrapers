from pupa.scrape import Scraper, Bill, VoteEvent
from pupa.utils.generic import convert_pdf
from datetime import datetime
import lxml.etree
import os
import re
import pytz
import scrapelib


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


class MSBillScraper(Scraper):
    _tz = pytz.timezone('CST6CDT')
    _action_types = (
        ('Died in Committee', 'committee-failure'),
        ('Enrolled Bill Signed', None),
        ('Immediate Release', None),
        ('Passed', 'passage'),
        ('Adopted', 'passage'),
        ('Amended', 'amendment-passage'),
        ('Failed', 'failure'),
        ('Committee Substitute Adopted', 'substitution'),
        ('Amendment Failed', 'amendment-failure'),
        ('Amendment Withdrawn', 'amendment-withdrawal'),
        ('Referred To', 'referral-committee'),
        ('Rereferred To', 'referral-committee'),
        ('Transmitted To', 'introduction'),
        ('Approved by Governor', 'executive-signature'),
        ('Vetoed', 'executive-veto'),
        ('Partially Vetoed', 'executive-veto-line-item'),
        ('Title Suff Do', 'committee-passage'),
        ('Read the Third Time', 'reading-3'),
    )

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_bills(chamber, session)

    def scrape_bills(self, chamber_to_scrape, session):
        url = 'http://billstatus.ls.state.ms.us/%s/pdf/all_measures/allmsrs.xml' % session

        bill_dir_page = self.get(url)
        root = lxml.etree.fromstring(bill_dir_page.content)
        for mr in root.xpath('//LASTACTION/MSRGROUP'):
            bill_id = mr.xpath('string(MEASURE)').replace(" ", "")
            if bill_id[0] == "S":
                chamber = "upper"
            else:
                chamber = "lower"

            bill_type = {'B': 'bill', 'C': 'concurrent resolution',
                         'R': 'resolution', 'N': 'nomination'}[bill_id[1]]

            # just skip past bills that are of the wrong chamber
            if chamber != chamber_to_scrape:
                continue

            link = mr.xpath('string(ACTIONLINK)').replace("..", "")
            main_doc = mr.xpath('string(MEASURELINK)').replace("../../../", "")
            main_doc_url = 'http://billstatus.ls.state.ms.us/%s' % main_doc
            bill_details_url = 'http://billstatus.ls.state.ms.us/%s/pdf%s' % (session, link)
            try:
                details_page = self.get(bill_details_url)
            except scrapelib.HTTPError:
                self.warning('Bill page not loading for {}; skipping'.format(bill_id))
                continue

            page = details_page.content
            # Some pages have the (invalid) byte 11 sitting around. Just drop
            # them out. Might as well.

            details_root = lxml.etree.fromstring(page)
            title = details_root.xpath('string(//SHORTTITLE)')
            longtitle = details_root.xpath('string(//LONGTITLE)')

            bill = Bill(bill_id,
                        legislative_session=session,
                        chamber=chamber,
                        title=title,
                        classification=bill_type)
            bill.extras['summary'] = longtitle
            bill.add_source(main_doc_url)
            # sponsors
            main_sponsor = details_root.xpath('string(//P_NAME)').split()
            if main_sponsor:
                main_sponsor = main_sponsor[0]
                main_sponsor_link = details_root.xpath('string(//P_LINK)').replace(" ", "_")
                main_sponsor_url = ('http://billstatus.ls.state.ms.us/%s/'
                                    'pdf/%s') % (session, main_sponsor_link.strip('../'))
                type = "primary"
                bill.add_source(main_sponsor_url)
                bill.add_sponsorship(main_sponsor,
                                     classification=type,
                                     entity_type='person',
                                     primary=True)

            for author in details_root.xpath('//AUTHORS/ADDITIONAL'):
                leg = author.xpath('string(CO_NAME)').replace(" ", "_")
                if leg:
                    leg_url = ('http://billstatus.ls.state.ms.us/%s/'
                               'pdf/House_authors/%s.xml') % (session, leg)
                    type = "cosponsor"
                    bill.add_source(leg_url)
                    bill.add_sponsorship(leg,
                                         classification=type,
                                         entity_type='person',
                                         primary=False
                                         )
            # Versions
            curr_version = details_root.xpath('string(//CURRENT_OTHER'
                                              ')').replace("../../../../", "")
            if curr_version != "":
                curr_version_url = "http://billstatus.ls.state.ms.us/" \
                        + curr_version
                bill.add_version_link("Current version", curr_version_url,
                                      on_duplicate="ignore",
                                      media_type="text/html"
                                      )

            intro_version = details_root.xpath('string(//INTRO_OTHER)').replace("../../../../", "")
            if intro_version != "":
                intro_version_url = "http://billstatus.ls.state.ms.us/"\
                        + intro_version
                bill.add_version_link("As Introduced", intro_version_url,
                                      on_duplicate='ignore',
                                      media_type='text/html')

            comm_version = details_root.xpath('string(//CMTESUB_OTHER'
                                              ')').replace("../../../../", "")
            if comm_version.find("documents") != -1:
                comm_version_url = "http://billstatus.ls.state.ms.us/" + comm_version
                bill.add_version_link("Committee Substitute", comm_version_url,
                                      on_duplicate='ignore',
                                      media_type='text/html')
            passed_version = details_root.xpath('string(//PASSED_OTHER'
                                                ')').replace("../../../../", "")
            if passed_version.find("documents") != -1:
                passed_version_url = "http://billstatus.ls.state.ms.us/" + passed_version
                title = "As Passed the " + chamber
                bill.add_version_link(title, passed_version_url,
                                      on_duplicate='ignore',
                                      media_type='text/html')

            asg_version = details_root.xpath('string(//ASG_OTHER)').replace("../../../../", "")
            if asg_version.find("documents") != -1:
                asg_version_url = "http://billstatus.ls.state.ms.us/" + asg_version
                bill.add_version_link("Approved by the Governor", asg_version_url,
                                      on_duplicate='ignore',
                                      media_type='text/html')

            # avoid duplicate votes
            seen_votes = set()

            # Actions
            for action in details_root.xpath('//HISTORY/ACTION'):
                # action_num  = action.xpath('string(ACT_NUMBER)').strip()
                # action_num = int(action_num)
                act_vote = action.xpath('string(ACT_VOTE)').replace("../../../..", "")
                action_desc = action.xpath('string(ACT_DESC)')
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

                if "Veto" in action and actor == 'executive':
                    version_path = details_root.xpath("string(//VETO_OTHER)")
                    version_path = version_path.replace("../../../../", "")
                    version_url = "http://billstatus.ls.state.ms.us/" + version_path
                    bill.add_document_link("Veto", version_url)

                atype = 'other'
                for prefix, prefix_type in self._action_types:
                    if action.startswith(prefix):
                        atype = prefix_type
                        break

                bill.add_action(action, self._tz.localize(date),
                                chamber=actor,
                                classification=atype if atype != 'other' else None)

                # use committee names as scraped subjects
                subjects = details_root.xpath('//H_NAME/text()')
                subjects += details_root.xpath('//S_NAME/text()')

                for subject in subjects:
                    if subject not in bill.subject:
                        bill.add_subject(subject)

                if act_vote:
                    vote_url = 'http://billstatus.ls.state.ms.us%s' % act_vote
                    if vote_url not in seen_votes:
                        seen_votes.add(vote_url)
                        yield from self.scrape_votes(vote_url, action,
                                                     date, actor, bill)

            bill.add_source(bill_details_url)
            yield bill

    _vote_mapping = {
        'Passed': ('Passage', True),
        'Adopted': ('Passage', True),
        'Failed': ('Passage', False),
        'Passed As Amended': ('Passage as Amended', True),
        'Adopted As Amended': ('Passage as Amended', True),
        'Appointment Confirmed': ('Appointment Confirmation', True),
        'Committee Substitute Adopted': ('Adopt Committee Substitute', True),
        'Committee Substitute Failed': ('Adopt Committee Substitute', False),
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

    def scrape_votes(self, url, motion, date, chamber, bill):
        vote_pdf, resp = self.urlretrieve(url)
        text = convert_pdf(vote_pdf, 'text')
        os.remove(vote_pdf)

        # this way we get a key error on a missing vote type
        motion, passed = self._vote_mapping[motion]

        yes_votes = []
        no_votes = []
        other_votes = []
        absent_votes = []
        not_voting_votes = []
        # point at array to add names to
        cur_array = None

        precursors = (
            ('yeas--', yes_votes),
            ('nays--', no_votes),
            ('absent or those not voting--', absent_votes),
            ('absent and those not voting--', absent_votes),
            ('not voting--', not_voting_votes),
            ('voting present--', other_votes),
            ('present--', other_votes),
            ('disclaimer', None),
        )

        # split lines on newline, recombine lines that don't end in punctuation
        lines = _combine_lines(text.decode().split('\n'))

        for line in lines:

            # check if the line starts with a precursor, switch to that array
            for pc, arr in precursors:
                if pc in line.lower():
                    cur_array = arr
                    line = line.replace(pc, '')

            # split names
            for name in line.split(','):
                name = name.strip()

                # move on if that's all there was
                if not name:
                    continue

                # None or a Total indicate the end of a section
                if 'None.' in name:
                    cur_array = None

                match = re.match(r'(.+?)\. Total--.*', name)
                if match:
                    cur_array.append(match.groups()[0])
                    cur_array = None

                # append name if it looks ok
                junk_in_name = False
                for junk in ('on final passage', 'Necessary', 'who would have',
                             'being a tie', 'therefore', 'Vacancies', 'a pair',
                             'Total-', 'ATTORNEY', 'on final passage',
                             'SPEAKER', 'BOARD', 'TREASURER', 'GOVERNOR',
                             'ARCHIVES', 'SECRETARY'):
                    if junk in name:
                        junk_in_name = True
                        break
                if cur_array is not None and not junk_in_name:
                    # strip trailing .
                    if name[-1] == '.':
                        name = name[:-1]
                    cur_array.append(name)

        # return vote object
        yes_count = len(yes_votes)
        no_count = len(no_votes)
        absent_count = len(absent_votes)
        not_voting_count = len(not_voting_votes)
        other_count = len(other_votes)

        vote = VoteEvent(chamber=chamber,
                         start_date=self._tz.localize(date),
                         motion_text=motion,
                         result='pass' if passed else 'fail',
                         classification='passage',
                         bill=bill)
        vote.pupa_id = url + '#' + bill.identifier

        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('absent', absent_count)
        vote.set_count('not voting', not_voting_count)
        vote.set_count('other', other_count)
        vote.add_source(url)
        for yes_vote in yes_votes:
            vote.vote('yes', yes_vote)
        for no_vote in no_votes:
            vote.vote('no', no_vote)
        for absent_vote in absent_votes:
            vote.vote('absent', absent_vote)
        for not_voting_vote in not_voting_votes:
            vote.vote('not voting', not_voting_vote)
        for other_vote in other_votes:
            vote.vote('other', other_vote)
        yield vote
