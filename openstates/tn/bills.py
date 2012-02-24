from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import datetime
import lxml.html
import re

_categorizers = (
    ('Amendment adopted', 'amendment:passed'),
    ('Amendment failed', 'amendment:failed'),
    ('Amendment proposed', 'amendment:introduced'),
    ('adopted am.', 'amendment:passed'),
    ('Am. withdrawn', 'amendment:withdrawn'),
    ('Divided committee report', 'committee:passed'),
    ('Filed for intro.', ['bill:introduced', 'bill:reading:1']),
    ('Reported back amended, do not pass', 'committee:passed:unfavorable'),
    ('Reported back amended, do pass', 'committee:passed:favorable'),
    ('Rec. For Pass.', 'committee:passed:favorable'),
    ('Rec. For pass.', 'committee:passed:favorable'),
    ('Reported back amended, without recommendation', 'committee:passed'),
    ('Reported back, do not pass', 'committee:passed:unfavorable'),
    ('w/ recommend', 'committee:passed:favorable'),
    ('Ref. to', 'committee:referred'),
    ('ref. to', 'committee:referred'),
    ('Assigned to', 'committee:referred'),
    ('Recieved from House', 'bill:introduced'),
    ('Recieved from Senate', 'bill:introduced'),
    ('Adopted, ', ['bill:passed']),
    ('Passed H., ', ['bill:passed']),
    ('Passed S., ', ['bill:passed']),
    ('Second reading, adopted', ['bill:passed', 'bill:reading:2']),
    ('Second reading, failed', ['bill:failed', 'bill:reading:2']),
    ('Second reading, passed', ['bill:passed', 'bill:reading:2']),
    ('Transmitted to Gov. for action.', 'governor:received'),
    ('Transmitted to Governor for his action.', 'governor:received'),
    ('Signed by Governor, but item veto', 'governor:vetoed:line-item'),
    ('Signed by Governor', 'governor:signed'),
    ('Withdrawn', 'bill:withdrawn'),
)

def categorize_action(action):
    for prefix, types in _categorizers:
        if prefix in action:
            return types
    return 'other'

def actions_from_table(bill, chamber, actions_table):
    action_rows = actions_table.xpath("tr[position()>1]")
    for ar in action_rows:
        tds = ar.xpath('td')
        action_taken = tds[0].text
        action_date = datetime.datetime.strptime(tds[1].text.strip(),
                                                 '%m/%d/%Y')
        action_type = categorize_action(action_taken)
        bill.add_action(chamber, action_taken, action_date, action_type)


class TNBillScraper(BillScraper):
    state = 'tn'

    def scrape(self, chamber, term):

        if chamber == 'lower':
            raise ValueError('TN can only be run with chamber=upper')

        #types of bills
        abbrs = ['HB', 'HJR', 'HR', 'SB','SJR', 'SR']

        for abbr in abbrs:

            if 'B' in abbr:
                bill_type = 'bill'
            elif 'JR' in abbr:
                bill_type = 'joint resolution'
            else:
                bill_type = 'resolution'

            #Checks if current term
            if term == self.metadata["terms"][-1]["sessions"][0]:
                bill_listing = 'http://wapp.capitol.tn.gov/apps/indexes/BillIndex.aspx?StartNum=%s0001&EndNum=%s9999' % (abbr, abbr)
            else:
                bill_listing = 'http://wapp.capitol.tn.gov/apps/archives/BillIndex.aspx?StartNum=%s0001&EndNum=%s9999&Year=%s' % (abbr, abbr, term)

            with self.urlopen(bill_listing) as bill_list_page:
                bill_list_page = lxml.html.fromstring(bill_list_page)
                for bill_links in bill_list_page.xpath('////div[@id="open"]//a'):
                    bill_link = bill_links.attrib['href']
                    if '..' in bill_link:
                        bill_link = 'http://wapp.capitol.tn.gov/apps' + bill_link[2:len(bill_link)]
                    self.scrape_bill(term, bill_link, bill_type)

    def scrape_bill(self, term, bill_url, bill_type):

        with self.urlopen(bill_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(bill_url)

            bill_id = page.xpath('//span[@id="lblBillSponsor"]/a[1]')[0].text
            secondary_bill_id = page.xpath('//span[@id="lblCoBillSponsor"]/a[1]')

            # checking if there is a matching bill
            if secondary_bill_id:
                secondary_bill_id = secondary_bill_id[0].text

                # swap ids if * is in secondary_bill_id
                if '*' in secondary_bill_id:
                    bill_id, secondary_bill_id = secondary_bill_id, bill_id
                    secondary_bill_id = secondary_bill_id.strip()

            bill_id = bill_id.replace('*', '').strip()

            primary_chamber = 'lower' if 'H' in bill_id else 'upper'
            secondary_chamber = 'upper' if primary_chamber == 'lower' else 'lower'

            title = page.xpath("//span[@id='lblAbstract']")[0].text

            # bill subject
            subject_pos = title.find('-')
            subjects = [s.strip() for s in title[:subject_pos-1].split(',')]

            bill = Bill(term, primary_chamber, bill_id, title, type=bill_type,
                        subjects=subjects)
            if secondary_bill_id:
                bill['alternate_bill_ids'] = [secondary_bill_id]
            bill.add_source(bill_url)

            # Primary Sponsor
            sponsor = page.xpath("//span[@id='lblBillSponsor']")[0].text_content().split("by")[-1]
            sponsor = sponsor.replace('*','').strip()
            bill.add_sponsor('primary',sponsor)

            # bill text
            summary = page.xpath("//span[@id='lblBillSponsor']/a")[0]
            bill.add_version('Current Version', summary.get('href'))

            # actions
            atable = page.xpath("//table[@id='tabHistoryAmendments_tabHistory_gvBillActionHistory']")[0]
            actions_from_table(bill, primary_chamber, atable)

            # if there is a matching bill
            if secondary_bill_id:
                # secondary sponsor
                secondary_sponsor = page.xpath("//span[@id='lblCoBillSponsor']")[0].text_content().split("by")[-1]
                secondary_sponsor = secondary_sponsor.replace('*','').replace(')', '').strip()
                bill.add_sponsor('secondary', secondary_sponsor)

                # secondary actions
                cotable = page.xpath("//table[@id='tabHistoryAmendments_tabHistory_gvCoActionHistory']")[0]
                actions_from_table(bill, secondary_chamber, cotable)

            # votes
            votes_link = page.xpath("//span[@id='lblBillVotes']/a/@href")
            if len(votes_link) > 0:
                bill = self.scrape_votes(bill, votes_link[0])
            votes_link = page.xpath("//span[@id='lblCompVotes']/a/@href")
            if len(votes_link) > 0:
                bill = self.scrape_votes(bill, votes_link[0])

            bill['actions'].sort(key=lambda a: a['date'])
            self.save_bill(bill)


    def scrape_votes(self, bill, link):
        with self.urlopen(link) as page:
            page = lxml.html.fromstring(page)
            raw_vote_data = page.xpath("//span[@id='lblVoteData']")[0].text_content()
            raw_vote_data = re.split('\w+? by \w+?\s+-', raw_vote_data.strip())[1:]
            for raw_vote in raw_vote_data:
                raw_vote = raw_vote.split(u'\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0')
                motion = raw_vote[0]

                vote_date = re.search('(\d+/\d+/\d+)', motion)
                if vote_date:
                    vote_date = datetime.datetime.strptime(vote_date.group(), '%m/%d/%Y')

                passed = ('Passed' in motion) or ('Adopted' in raw_vote[1])
                vote_regex = re.compile('\d+$')
                aye_regex = re.compile('^.+voting aye were: (.+) -')
                no_regex = re.compile('^.+voting no were: (.+) -')
                other_regex = re.compile('^.+present and not voting were: (.+) -')
                yes_count = 0
                no_count = 0
                other_count = 0
                ayes = []
                nos = []
                others = []

                for v in raw_vote[1:]:
                    v = v.strip()
                    if v.startswith('Ayes...') and vote_regex.search(v):
                        yes_count = int(vote_regex.search(v).group())
                    elif v.startswith('Noes...') and vote_regex.search(v):
                        no_count = int(vote_regex.search(v).group())
                    elif v.startswith('Present and not voting...') and vote_regex.search(v):
                        other_count += int(vote_regex.search(v).group())
                    elif aye_regex.search(v):
                        ayes = aye_regex.search(v).groups()[0].split(', ')
                    elif no_regex.search(v):
                        nos = no_regex.search(v).groups()[0].split(', ')
                    elif other_regex.search(v):
                        others += other_regex.search(v).groups()[0].split(', ')

                vote = Vote(bill['chamber'], vote_date, motion, passed, yes_count, no_count, other_count)
                vote.add_source(link)
                for a in ayes:
                    vote.yes(a)
                for n in nos:
                    vote.no(n)
                for o in others:
                    vote.other(o)

                vote.validate()
                bill.add_vote(vote)

        return bill
