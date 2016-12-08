from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import re
import datetime
from collections import defaultdict
import lxml.html

BILLS_URL = 'http://legislature.idaho.gov/legislation/%s/minidata.htm'
BILL_URL = 'http://legislature.idaho.gov/legislation/%s/%s.htm'

_CHAMBERS = {'upper':'Senate', 'lower':'House'}

_BILL_TYPES = {'CR':'concurrent resolution',
              'JM': 'joint memorial', 'JR': 'joint resolution',
              'P': 'proclamation', 'R': 'resolution'}
_COMMITTEES = { 'lower': {'Loc Gov':'Local Government',
                     'Jud':'Judiciary, Rules and Administration',
                     'Res/Con':'Resources and Conservation',
                     'Com/HuRes':'Commerce and Human Resources',
                     'Transp':'Transportation and Defense',
                     'St Aff': 'State Affairs',
                     'Rev/Tax':'Revenues and Taxation',
                     'Health/Wel':'Health and Welfare',
                     'Env':'Environment, Energy and Technology',
                     'Bus':'Business', 'Educ':'Education',
                     'Agric Aff':'Agricultural Affairs',
                     'Approp': 'Appropriations','W/M': 'Ways and Means'},
                'upper': {'Agric Aff': 'Agricultural Affairs',
                     'Com/HuRes':'Commerce and Human Resources',
                     'Educ': 'Education', 'Fin':'Finance',
                     'Health/Wel':'Health and Welfare',
                     'Jud': 'Judiciary and Rules',
                     'Loc Gov': 'Local Government and Taxation',
                     'Res/Env': 'Resources and Environment',
                     'St Aff': 'State Affairs', 'Transp': 'Transportation'}
                }

# a full list of the abbreviations and definitions can be found at:
# http://legislature.idaho.gov/sessioninfo/glossary.htm
# background on bill to law can be found at:
# http://legislature.idaho.gov/about/jointrules.htm
_ACTIONS = (
     # bill:reading:1
     (r'(\w+) intro - (\d)\w+ rdg - to (\w+/?\s?\w+\s?\w+)',
      lambda mch, ch: ["bill:introduced", "bill:reading:1", "committee:referred"] \
                        if mch.groups()[2] in _COMMITTEES[ch] else ["bill:introduced", "bill:reading:1"] ),
     # committee actions
     (r'rpt prt - to\s(\w+/?\s?\w+)',
      lambda mch, ch: ["committee:referred"] if mch.groups()[0] in _COMMITTEES[ch] \
                                             else "other"),
     # it is difficult to figure out which committee passed/reported out a bill
     # but i guess we at least know that only committees report out
     (r'rpt out - rec d/p', "committee:passed:favorable"),
     (r'^rpt out', 'committee:passed'),


    (r'^Reported Signed by Governor', "governor:signed"),
    (r'^Signed by Governor', "governor:signed"),

     # I dont recall seeing a 2nd rdg by itself
     (r'^1st rdg - to 2nd rdg', "bill:reading:2"),
     # second to third will count as a third read if there is no
     # explicit third reading action
     (r'2nd rdg - to 3rd rdg', "bill:reading:3"),
     (r'^3rd rdg$', "bill:reading:3"),
     (r'.*Third Time.*PASSED.*', ["bill:reading:3", "bill:passed"]),
     # bill:reading:3, bill:passed
     (r'^3rd rdg as amen - (ADOPTED|PASSED)', ["bill:reading:3", "bill:passed"]),
     (r'^3rd rdg - (ADOPTED|PASSED)', ["bill:reading:3", "bill:passed"]),
     (r'^Read Third Time in Full .* (ADOPTED|PASSED).*', [
         "bill:reading:3", "bill:passed"]),
     (r'^.*read three times - (ADOPTED|PASSED).*', [
         "bill:reading:3", "bill:passed"]),
     (r'^.*Read in full .* (ADOPTED|PASSED).*', [
         "bill:reading:3", "bill:passed"]),
     # bill:reading:3, bill:failed
     (r'^3rd rdg as amen - (FAILED)', ["bill:reading:3", "bill:failed"]),
     (r'^3rd rdg - (FAILED)', ["bill:reading:3", "bill:failed"]),
     # rules suspended
     (r'^Rls susp - (ADOPTED|PASSED|FAILED)', lambda mch, ch: {
                                                       'ADOPTED': "bill:passed",
                                                        'PASSED': "bill:passed",
                                                        'FAILED': "bill:failed"
                                                   }[mch.groups()[0]]),
     (r'^to governor', "governor:received"),
     (r'^Governor signed', "governor:signed"),
)
def get_action(actor, text):
    # the biggest issue with actions is that some lines seem to indicate more
    # than one action
    

    for pattern, action in _ACTIONS:
        match = re.match(pattern, text, re.I)
        if match:
            if callable(action):
                return action(match, actor)
            else:
                return action
    return "other"

def get_bill_type(bill_id):
    suffix = bill_id.split(' ')[0]
    if len(suffix) == 1:
        return 'bill'
    else:
        return _BILL_TYPES[suffix[1:]]

class IDBillScraper(BillScraper):
    jurisdiction = 'id'

    # the following are only used for parsing legislation from 2008 and earlier
    vote = None
    in_vote = False
    ayes = False
    nays = False
    other = False
    last_date = None


    def scrape_subjects(self, session):
        self._subjects = defaultdict(list)

        url = 'http://legislature.idaho.gov/legislation/%s/topicind.htm' % session
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # loop through anchors
        anchors = doc.xpath('//td[@width="95%"]//a')
        for a in anchors:
            # if anchor has a name, that's the subject
            if a.get('name'):
                subject = a.get('name')
            # if anchor is a link to a bill, save that reference
            elif 'legislation' in a.get('href'):
                self._subjects[a.text].append(subject)


    def scrape(self, chamber, session):
        """
        Scrapes all the bills for a given session and chamber
        """

        #url = BILLS_URL % session
        if int(session[:4]) < 2009:
            self.scrape_pre_2009(chamber, session)
        else:
            self.scrape_subjects(session)
            self.scrape_post_2009(chamber, session)

    def scrape_post_2009(self, chamber, session):
        "scrapes legislation for 2009 and above"
        url = BILLS_URL % session
        bill_index = self.get(url).text
        html = lxml.html.fromstring(bill_index)
        # I check for rows with an id that contains 'bill' and startswith
        # 'H' or 'S' to make sure I dont get any links from the menus
        # might not be necessary
        bill_rows = html.xpath('//tr[contains(@id, "bill") and '\
                               'starts-with(descendant::td/a/text(), "%s")]'\
                               % _CHAMBERS[chamber][0])
        for row in bill_rows:
            matches = re.match(r'([A-Z]*)([0-9]+)',
                                        row[0].text_content().strip())
            bill_id = " ".join(matches.groups()).strip()
            short_title = row[1].text_content().strip()
            self.scrape_bill(chamber, session, bill_id, short_title)

    def scrape_pre_2009(self, chamber, session):
        """scrapes legislation from 2008 and below."""
        url = BILLS_URL + 'l'
        url = url % session
        bill_index = self.get(url).text
        html = lxml.html.fromstring(bill_index)
        html.make_links_absolute(url)
        links = html.xpath('//a')
        exprs = r'(%s[A-Z]*)([0-9]+)' % _CHAMBERS[chamber][0]
        for link in links:
            matches = re.match(exprs, link.text)
            if matches:
                bill_id = " ".join(matches.groups())
                short_title = link.tail[:link.tail.index('..')]
                self.scrape_pre_2009_bill(chamber, session, bill_id, short_title)

    def scrape_bill(self, chamber, session, bill_id, short_title=None):
        """
        Scrapes documents, actions, vote counts and votes for
        bills from the 2009 session and above.
        """
        url = BILL_URL % (session, bill_id.replace(' ', ''))
        bill_page = self.get(url).text
        html = lxml.html.fromstring(bill_page)
        html.make_links_absolute('http://legislature.idaho.gov/legislation/%s/' % session)
        bill_tables = html.xpath('./body/table/tr/td[2]')[0].xpath('.//table')
        title = bill_tables[1].text_content().strip()
        bill_type = get_bill_type(bill_id)
        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)
        bill['subjects'] = self._subjects[bill_id.replace(' ', '')]

        if short_title and bill['title'].lower() != short_title.lower():
            bill.add_title(short_title)

        # documents
        doc_links = html.xpath('//span/a')
        for link in doc_links:
            name = link.text_content().strip()
            href = link.get('href')
            if 'Engrossment' in name or 'Bill Text' in name:
                bill.add_version(name, href, mimetype='application/pdf')
            else:
                bill.add_document(name, href)

        def _split(string):
            return re.split(r"\w+[,|AND]\s+", string)

        # sponsors range from a committee to one legislator to a group of legs
        sponsor_lists = bill_tables[0].text_content().split('by')
        if len(sponsor_lists) > 1:
            for sponsors in sponsor_lists[1:]:
                for person in _split(sponsors):
                    person = person.strip()
                    if person != "":
                        bill.add_sponsor('primary', person)

        actor = chamber
        last_date = None
        for row in bill_tables[2]:
            # lots of empty rows
            if len(row) == 1:
                continue
            _, date, action, _ = [x.text_content().strip() for x in row]

            if date:
                last_date = date
            else:
                date = last_date

            date = datetime.datetime.strptime(date+ '/' + session[0:4],
                                              "%m/%d/%Y")
            if action.startswith('House'):
                actor = 'lower'
            elif action.startswith('Senate'):
                actor = 'upper'

            # votes
            if 'AYES' in action or 'NAYS' in action:
                vote = self.parse_vote(actor, date, row[2])
                vote.add_source(url)
                bill.add_vote(vote)
            # some td's text is seperated by br elements
            if len(row[2]):
                action = "".join(row[2].itertext())
            action = action.replace(u'\xa0', ' ').strip()
            atype = get_action(actor, action)
            bill.add_action(actor, action, date, type=atype)
            # after voice vote/roll call and some actions the bill is sent
            # 'to House' or 'to Senate'
            if 'to House' in action:
                actor = 'lower'
            elif 'to Senate' in action:
                actor = 'upper'
        self.save_bill(bill)

    def scrape_pre_2009_bill(self, chamber, session, bill_id, short_title=''):
        """bills from 2008 and below are in a 'pre' element and is simpler to
        parse them as text"""
        url = 'http://legislature.idaho.gov/legislation/%s/%s.html' % (session, bill_id.replace(' ', ''))
        bill_page = self.get(url).text
        html = lxml.html.fromstring(bill_page)
        text = html.xpath('//pre')[0].text.split('\r\n')

        # title
        title = " - ".join([ x.strip() for x in text[1].split('-') if x.isupper() ])
        # bill type
        bill_type = get_bill_type(bill_id)

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        # sponsors
        sponsors = text[0].split('by')[-1]
        for sponsor in sponsors.split(','):
            bill.add_sponsor('primary', sponsor)

        actor = chamber
        self.flag() # clear last bills vote flags
        self.vote = None #

        for line in text:

            if re.match(r'^\d\d/\d\d', line):
                date = date = datetime.datetime.strptime(line[0:5] + '/' + session[0:4],
                                              "%m/%d/%Y")
                self.last_date = date
                action_text = line[5:].strip()
                # actor
                if action_text.lower().startswith('house') or \
                   action_text.lower().startswith('senate'):
                    actor = {'H':'lower', 'S':'upper'}[action_text[0]]

                action = get_action(actor, action_text)
                bill.add_action(actor,action_text, date, type=action)
                if "bill:passed" in action or "bill:failed" in action:
                    passed = False if 'FAILED' in action_text else True
                    votes = re.search(r'(\d+)-(\d+)-(\d+)', action_text)
                    if votes:
                        yes, no, other = votes.groups()
                        self.in_vote = True
                        self.vote = Vote(chamber, date, action_text, passed,
                                     int(yes), int(no), int(other))
            else:
                date = self.last_date
                # nothing to do if its not a vote
                if "Floor Sponsor" in line:
                    self.in_vote = False
                    if self.vote:
                        bill.add_vote(self.vote)
                        self.vote = None

                if not self.in_vote:
                    continue
                if 'AYES --' in line:
                    self.flag(ayes=True)
                elif 'NAYS --' in line:
                    self.flag(nays=True)
                elif 'Absent and excused' in line:
                    self.flag(other=True)

                if self.ayes:
                    for name in line.replace('AYES --', '').split(','):
                        name = name.strip()
                        if name:
                            self.vote.yes(name)

                if self.nays:
                    for name in line.replace('NAYS --', '').split(','):
                        name = name.strip()
                        if name:
                            self.vote.no(name)

                if self.other:
                    for name in line.replace('Absent and excused --', '').split(','):
                        name = name.strip()
                        if name:
                            self.vote.other(name)

        self.save_bill(bill)

    def get_names(self,name_text):
        if name_text:
            #both of these are unicode non-breaking spaces
            name_text = name_text.replace(u'\xa0--\xa0', '')
            name_text = name_text.replace(u'\u00a0',' ')
            name_list = [name.strip() for name in name_text.split(",") if name]
            return name_list
        return []

    def parse_vote(self, actor, date, row):
        """
        takes the actor, date and row element and returns a Vote object
        """
        spans = row.xpath('.//span')
        motion = row.text.replace(u'\u00a0'," ").replace("-","").strip()
        motion = motion if motion else "passage"
        passed, yes_count, no_count, other_count = spans[0].text_content().rsplit('-',3)
        yes_votes = self.get_names(spans[1].tail)
        no_votes = self.get_names(spans[2].tail)

        other_votes = []
        for span in spans[3:]:
            if span.text.startswith(('Absent', 'Excused')):
                other_votes += self.get_names(span.tail)
        for key, val in {'adopted': True, 'passed': True, 'failed':False}.items():
            if key in passed.lower():
                passed = val
                break
        vote = Vote(actor, date, motion, passed, int(yes_count), int(no_count),
                    int(other_count))
        for name in yes_votes:
            if name and name != 'None':
                vote.yes(name)
        for name in no_votes:
            if name and name != 'None':
                vote.no(name)
        for name in other_votes:
            if name and name != 'None':
                vote.other(name)
        return vote

    def flag(self, ayes=False, nays=False, other=False):
        """ help to keep track of where we are at parsing votes from text"""
        self.ayes = ayes
        self.nays = nays
        self.other = other
