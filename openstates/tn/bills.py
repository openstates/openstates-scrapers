import datetime
import lxml.html
import re
from collections import namedtuple

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class Rule(namedtuple('Rule', 'regex types stop attrs')):
    '''If ``regex`` matches the action text, the resulting action's
    types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    '''
    def __new__(_cls, regex, types=None, stop=True, **kwargs):
        'Create new instance of Rule(regex, types, attrs, stop)'

        # Types can be a string or a sequence.
        if isinstance(types, basestring):
            types = set([types])
        types = set(types or [])

        # If no types are associated, assume that the categorizer
        # should continue looking at other rules.
        if not types:
            stop = False
        return tuple.__new__(_cls, (regex, types, stop, kwargs))


# These are regex patterns that map to action categories.
_categorizer_rules = (

    # Some actions are listed in the wrong chamber column.
    # Fix the chamber before moving on to the other rules.
    Rule(r'^H\.\s', stop=False, actor='lower'),
    Rule(r'^S\.\s', stop=False, actor='upper'),
    Rule(r'Signed by S\. Speaker', actor='upper'),
    Rule(r'Signed by H\. Speaker', actor='lower'),

    # Extract the vote counts to help disambiguate chambers later.
    Rule(r'Ayes\s*(?P<yes_votes>\d+),\s*Nays\s*(?P<no_votes>\d+)', stop=False),

    # Committees
    Rule(r'(?i)ref\. to (?P<committees>.+?Comm\.)', 'committee:referred'),
    Rule(r'^Failed In S\.(?P<committees>.+?Comm\.)', 'committee:failed'),
    Rule(r'^Failed In s/c (?P<committees>.+)', 'committee:failed'),
    Rule(r'Rcvd\. from H., ref\. to S\. (?P<committees>.+)',
         'committee:referred', actor='upper'),
    Rule(r'Placed on cal\. (?P<committees>.+?) for', stop=False),
    Rule(r'Taken off notice for cal in s/c (?P<committees>.+)'),
    Rule(r'to be heard in (?P<committees>.+?Comm\.)'),
    Rule(r'Action Def. in S. (?P<committees>.+?Comm.)',
         actor='upper'),
    Rule(r'(?i)Placed on S. (?P<committees>.+?Comm\.) cal. for',
         actor='upper'),
    Rule(r'(?i)Assigned to (?P<committees>.+?comm\.)'),
    Rule(r'(?i)Placed on S. (?P<committees>.+?Comm.) cal.',
         actor='upper'),
    Rule(r'(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)'),
    Rule(r'(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)'),
    Rule(r'(?i)Taken off Notice For cal\. in[: ]+(?!s/c)(?P<committees>.+)'),
    Rule(r'(?i)Re-referred To:\s+(?P<committees>.+)', 'committee:referred'),
    Rule(r'Recalled from S. (?P<committees>.+?Comm.)'),

    # Amendments
    Rule(r'^Am\..+?tabled', 'amendment:tabled'),
    Rule('^Am\. withdrawn\.\(Amendment \d+ \- (?P<version>\S+)',
         'amendment:withdrawn'),
    Rule(r'^Am\. reconsidered(, withdrawn)?\.\(Amendment \d \- (?P<version>.+?\))',
         'amendment:withdrawn'),
    Rule(r'adopted am\.\(Amendment \d+ of \d+ - (?P<version>\S+)\)',
         'amendment:passed'),
    Rule(r'refused to concur.+?in.+?am', 'amendment:failed'),

    # Bill passage
    Rule(r'^Passed H\.', 'bill:passed', actor='lower'),
    Rule(r'^Passed S\.', 'bill:passed', actor='upper'),
    Rule(r'^R/S Adopted', 'bill:passed'),
    Rule(r'R/S Intro., adopted', 'bill:passed'),
    Rule(r'R/S Concurred', 'bill:passed'),

    # Veto
    Rule(r'(?i)veto', 'governor:vetoed'),

    # The existing rules for TN categorization:
    Rule('Amendment adopted', 'amendment:passed'),
    Rule('Amendment failed', 'amendment:failed'),
    Rule('Amendment proposed', 'amendment:introduced'),
    Rule('adopted am.', 'amendment:passed'),
    Rule('Am. withdrawn', 'amendment:withdrawn'),
    Rule('Divided committee report', 'committee:passed'),
    Rule('Filed for intro.', ['bill:introduced', 'bill:reading:1']),
    Rule('Reported back amended, do not pass', 'committee:passed:unfavorable'),
    Rule('Reported back amended, do pass', 'committee:passed:favorable'),
    Rule('Rec. For Pass.', 'committee:passed:favorable'),
    Rule('Rec. For pass.', 'committee:passed:favorable'),
    Rule('Reported back amended, without recommendation', 'committee:passed'),
    Rule('Reported back, do not pass', 'committee:passed:unfavorable'),
    Rule('w/ recommend', 'committee:passed:favorable'),
    Rule('Ref. to', 'committee:referred'),
    Rule('ref. to', 'committee:referred'),
    Rule('Assigned to', 'committee:referred'),
    Rule('Received from House', 'bill:introduced'),
    Rule('Received from Senate', 'bill:introduced'),
    Rule('Adopted, ', ['bill:passed']),
    Rule('Concurred, ', ['bill:passed']),
    Rule('Passed H., ', ['bill:passed']),
    Rule('Passed S., ', ['bill:passed']),
    Rule('Second reading, adopted', ['bill:passed', 'bill:reading:2']),
    Rule('Second reading, failed', ['bill:failed', 'bill:reading:2']),
    Rule('Second reading, passed', ['bill:passed', 'bill:reading:2']),
    Rule('Transmitted to Gov. for action.', 'governor:received'),
    Rule('Transmitted to Governor for his action.', 'governor:received'),
    Rule('Signed by Governor, but item veto', 'governor:vetoed:line-item'),
    Rule('Signed by Governor', 'governor:signed'),
    Rule('Withdrawn', 'bill:withdrawn'),
    Rule('tabled', 'amendment:tabled'),
    Rule('widthrawn', 'amendment:withdrawn'),
    Rule(r'Intro', 'bill:introduced'),
)


def categorize_action(action):
    types = set()
    attrs = {}

    for rule in _categorizer_rules:

        # Try to match the regex.
        m = re.search(rule.regex, action)
        if m or (rule.regex in action):
            # If so, apply its associated types to this action.
            types |= rule.types

            # Also add its specified attrs.
            attrs.update(m.groupdict())
            attrs.update(rule.attrs)

            # Break if the rule says so, otherwise continue testing against
            # other rules.
            if rule.stop is True:
                break

    # Returns types, attrs
    return list(types), attrs


def actions_from_table(bill, actions_table):
    '''
    '''
    action_rows = actions_table.xpath("tr")

    # first row will say "Actions Taken on S|H(B|R|CR)..."
    if 'Actions Taken on S' in action_rows[0].text_content():
        chamber = 'upper'
    else:
        chamber = 'lower'

    for ar in action_rows[1:]:
        tds = ar.xpath('td')
        action_taken = tds[0].text
        strptime = datetime.datetime.strptime
        action_date = strptime(tds[1].text.strip(), '%m/%d/%Y')
        action_types, attrs = categorize_action(action_taken)

        # Overwrite any presumtive fields that are inaccurate, usually chamber.
        action = dict(action=action_taken, date=action_date,
                      type=action_types, actor=chamber)
        action.update(**attrs)

        # Finally, if a vote tally is given, switch the chamber.
        if set(['yes_votes', 'no_votes']) & set(attrs):
            total_votes = int(attrs['yes_votes']) + int(attrs['no_votes'])
            if total_votes > 35:
                action['actor'] = 'lower'
            if total_votes <= 35:
                action['actor'] = 'upper'

        bill.add_action(**action)


class TNBillScraper(BillScraper):
    jurisdiction = 'tn'

    def scrape(self, term, chambers):

        #The index page gives us links to the paginated bill pages
        index_page = 'http://wapp.capitol.tn.gov/apps/indexes/'
        index_list_page = self.get(index_page).text
        index_list_page = lxml.html.fromstring(index_list_page)
        index_list_page.make_links_absolute(index_page)
        
        for bill_listing in index_list_page.xpath('//td[contains(@class,"webindex")]/a'):
            
            bill_listing = bill_listing.attrib['href'] 
       
            bill_list_page = self.get(bill_listing).text
            bill_list_page = lxml.html.fromstring(bill_list_page)
            bill_list_page.make_links_absolute(bill_listing)

            for bill_link in bill_list_page.xpath(
                '//h1[text()="Legislation"]/following-sibling::div/'
                'div/div/div/label//a/@href'
                ):
                self.scrape_bill(term, bill_link)

    def scrape_bill(self, term, bill_url):

        page = self.get(bill_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(bill_url)

        try:
            bill_id = page.xpath('//span[@id="lblBillNumber"]/a[1]')[0].text
        except IndexError:
            self.logger.warning("Something is wrong with bill page, skipping.")
            return
        secondary_bill_id = page.xpath('//span[@id="lblCompNumber"]/a[1]')

        # checking if there is a matching bill
        if secondary_bill_id:
            secondary_bill_id = secondary_bill_id[0].text
            # swap ids if * is in secondary_bill_id
            if '*' in secondary_bill_id:
                bill_id, secondary_bill_id = secondary_bill_id, bill_id
                secondary_bill_id = secondary_bill_id.strip()
            secondary_bill_id = secondary_bill_id.replace('  ',' ')
            
        bill_id = bill_id.replace('*', '').replace('  ',' ').strip()

        if 'B' in bill_id:
            bill_type = 'bill'
        elif 'JR' in bill_id:
            bill_type = 'joint resolution'
        elif 'R' in bill_id:
            bill_type = 'resolution'
            

        primary_chamber = 'lower' if 'H' in bill_id else 'upper'
        # secondary_chamber = 'upper' if primary_chamber == 'lower' else 'lower'

        title = page.xpath("//span[@id='lblAbstract']")[0].text
        if title is None:
            msg = '%s detail page was missing title info.'
            self.logger.warning(msg % bill_id)
            return

        # bill subject
        subject_pos = title.find('-')
        subjects = [s.strip() for s in title[:subject_pos - 1].split(',')]
        subjects = filter(None, subjects)

        bill = Bill(term, primary_chamber, bill_id, title, type=bill_type,
                    subjects=subjects)
        if secondary_bill_id:
            bill['alternate_bill_ids'] = [secondary_bill_id]
        bill.add_source(bill_url)

        # Primary Sponsor
        sponsor = page.xpath("//span[@id='lblBillPrimeSponsor']")[0].text_content().split("by")[-1]
        sponsor = sponsor.replace('*', '').strip()
        if sponsor:
            bill.add_sponsor('primary', sponsor)

        # bill text
        btext = page.xpath("//span[@id='lblBillNumber']/a")[0]
        bill.add_version('Current Version', btext.get('href'),
                         mimetype='application/pdf')

        # documents
        summary = page.xpath('//a[contains(@href, "BillSummaryArchive")]')
        if summary:
            bill.add_document('Summary', summary[0].get('href'))
        fiscal = page.xpath('//span[@id="lblFiscalNote"]//a')
        if fiscal:
            bill.add_document('Fiscal Note', fiscal[0].get('href'))
        amendments = page.xpath('//a[contains(@href, "/Amend/")]')
        for amendment in amendments:
            bill.add_document('Amendment ' + amendment.text,
                              amendment.get('href'))
        # amendment notes in image with alt text describing doc inside <a>
        amend_fns = page.xpath('//img[contains(@alt, "Fiscal Memo")]')
        for afn in amend_fns:
            bill.add_document(afn.get('alt'), afn.getparent().get('href'))

        # actions
        atable = page.xpath("//table[@id='gvBillActionHistory']")[0]
        actions_from_table(bill, atable)

        # if there is a matching bill
        if secondary_bill_id:
            # secondary sponsor
            secondary_sponsor = page.xpath("//span[@id='lblCompPrimeSponsor']")[0].text_content().split("by")[-1]
            secondary_sponsor = secondary_sponsor.replace('*', '').replace(')', '').strip()
            # Skip black-name sponsors.
            if secondary_sponsor:
                bill.add_sponsor('primary', secondary_sponsor)

            # secondary actions
            cotable = page.xpath("//table[@id='gvCoActionHistory']")[0]
            actions_from_table(bill, cotable)

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
        page = self.get(link).text
        page = lxml.html.fromstring(page)
        raw_vote_data = page.xpath("//span[@id='lblVoteData']")[0].text_content()
        raw_vote_data = re.split('\w+? by [\w ]+?\s+-', raw_vote_data.strip())[1:]
        for raw_vote in raw_vote_data:
            raw_vote = raw_vote.split(u'\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0')
            motion = raw_vote[0]

            vote_date = re.search('(\d+/\d+/\d+)', motion)
            if vote_date:
                vote_date = datetime.datetime.strptime(vote_date.group(), '%m/%d/%Y')

            passed = ('Passed' in motion or
                      'Recommended for passage' in motion or
                      'Adopted' in raw_vote[1]
                     )
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

            if 'ChamberVoting=H' in link:
                chamber = 'lower'
            else:
                chamber = 'upper'

            vote = Vote(chamber, vote_date, motion, passed, yes_count,
                        no_count, other_count)
            vote.add_source(link)

            seen = set()
            for a in ayes:
                if a in seen:
                    continue
                vote.yes(a)
                seen.add(a)
            for n in nos:
                if n in seen:
                    continue
                vote.no(n)
                seen.add(n)
            for o in others:
                if o in seen:
                    continue
                vote.other(o)
                seen.add(o)

            # vote.validate()
            bill.add_vote(vote)

        return bill
