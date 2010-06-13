# -*- coding: utf-8 -*-
import re
from urlparse import urljoin,urlsplit

from util import get_soup, get_text, elem_name, standardize_chamber
import votes

from fiftystates.scrape.il import year2session
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote


BASE_LEGISLATION_URL = "http://ilga.gov/legislation/default.asp?GA=%s"

TITLE_REMOVING_PATTERN = re.compile(".*(Rep|Sen). (.+)$")
SPONSOR_PATTERN = re.compile("^(Added |Removed )?(.+Sponsor) (Rep|Sen). (.+)$")

class ILBillScraper(BillScraper):

    state = 'il'

    def scrape(self, chamber, year):
        try:
            session = year2session[year]
        except KeyError:
            raise NoDataForYear(year)
        urls = get_all_bill_urls(self, chamber,session,types=['HB','SB'])
        for url in urls:
            self._scrape_bill(url)

    def _scrape_bill(self,url):
        try:
            bill = parse_bill(self, url)
            self.apply_votes(bill)
            self.save_bill(bill)
        except Exception, e:
            self.warning("Error parsing %s [%s] [%s]" % (url,e, type(e)))

    def apply_votes(self, bill):
        """Given a bill (and assuming it has a status_url in its dict), parse all of the votes
        """
        bill_votes = votes.all_votes_for_url(self, bill['status_url'])
        for (chamber,vote_desc,pdf_url,these_votes) in bill_votes:
            try:
                date = vote_desc.split("-")[-1]
            except IndexError:
                self.warning("[%s] Couldn't get date out of [%s]" % (bill['bill_id'],vote_desc))
                continue
            yes_votes = []
            no_votes = []
            other_votes = []
            for voter,vote in these_votes.iteritems():
                if vote == 'Y': 
                    yes_votes.append(voter)
                elif vote == 'N': 
                    no_votes.append(voter)
                else:
                    other_votes.append(voter)
            passed = len(yes_votes) > len(no_votes) # not necessarily correct, but not sure where else to get it. maybe from pdf
            vote = Vote(standardize_chamber(chamber),date,vote_desc,passed, len(yes_votes), len(no_votes), len(other_votes),pdf_url=pdf_url)
            for voter in yes_votes:
                vote.yes(voter)
            for voter in no_votes:
                vote.no(voter)
            for voter in other_votes:
                vote.other(voter)
            bill.add_vote(vote)

    def apply_votes_from_actions(self,bill):
        """Not quite clear on how to connect actions to vote PDFs, so this may not be usable.
        """
        for action_dict in bill['actions']:
            match = VOTE_ACTION_PATTERN.match(action_dict['action'])
            if match:
                motion,yes_count,no_count,other_count = match.groups()
                passed = int(yes_count) > int(no_count) # lame assumption - can we analyze the text instead?
                bill.add_vote(Vote(action_dict['actor'],action_dict['date'].strip(),motion.strip(),passed,int(yes_count),int(no_count),int(other_count)))


def parse_bill(scraper, url):
    """Given a bill status URL, return a fully loaded Bill object, except for votes, which
       are expected to be handled externally.
    """
    session = extract_session(url)
    chamber = chamber_for_doctype(extract_doctype(url))
    s = get_soup(scraper, url)
    bill_id = extract_bill_id(s)
    landmark = s(text=re.compile(".*Short Description.*"))
    name_span = landmark[0].findParent().findNextSibling()
    bill_name = get_text(name_span)
    bill = Bill(session, chamber, bill_id, bill_name.strip(),status_url=url)
    actions = extract_actions(s)
    for chamber,action,date in actions:
        bill.add_action(chamber,action,date) #kwargs are permitted if we have 'em.  
    sponsor_dict = extract_sponsors_from_actions([action[1] for action in actions])
    for type,namelist in sponsor_dict.iteritems():
        for name in namelist:
            bill.add_sponsor(type,name)
    for name,link in extract_versions(scraper, s):
        bill.add_version(name,link)
    return bill

def extract_versions(scraper, s):
    """Get the fulltext link from the page.
    visit it.
    get all links on that page that ref fulltext.asp
    skip the 'printer friendly' for the current page
    append '&print=true' to each of the links
    return a sequence of 2-tuples (name,link)
    """
    versions = []
    links = s("a", {"class": "legislinks", "href": re.compile(".*fulltext.asp.*")})
    if links:
        s = get_soup(scraper, urljoin(s.orig_url, links[0]['href']))
        links = s("a", {"href": re.compile(".*fulltext.asp.*"), "target": None}) # target is used for printer friendly, we'll skip that one.
        for link in links:
            versions.append((link.next, urljoin(s.orig_url,link['href'] + "&print=true")))
    return versions

def extract_sponsors_from_actions(actions):
    """Given a list of actions, decompose into a map whose keys are sponsorship types
       and whose values are lists of sponsors.
       
       We're assuming the first action always indicates a primary sponsor.
    """
    sponsor_dict = {}
    try:
        primary = pull_name_from_end(actions[0])
    except IndexError:
        return {}
    sponsor_dict.setdefault(u"Primary",[]).append(primary)
    for action in actions[1:]:
        match = SPONSOR_PATTERN.match(action)
        if match:
            (modification,type,title,name) = match.groups()
            if type.startswith("as "): type = type[3:]
            if (not modification) or modification.startswith("Added"):
                sponsor_dict.setdefault(type,[]).append(name)
            else:
                sponsor_dict[type].remove(name)
    return sponsor_dict

def pull_name_from_end(s):
    match = TITLE_REMOVING_PATTERN.match(s)
    if match:
        return match.groups()[1]
    return None

def extract_actions(s):
    actions = []
    anchor = s("a",{'name':'actions'})[0]
    table = None
    for x in anchor.nextGenerator():
        if hasattr(x,'name') and  getattr(x,'name') == 'table':
            table = x
            break
    if table:
        cells = table("td", { "class": "content" }) # markup bad: only header row correctly wrapped in a "tr"!
        while cells:
            (date,chamber,action) = cells[0:3]
            date = get_text(date).replace("&nbsp;"," ").strip()
            chamber = standardize_chamber(get_text(chamber).lower())
            cells = cells[3:]
            action = get_text(action)
            actions.append((chamber,action,date))
    return actions

def extract_bill_id(soup):
    title_text = soup("title")[0](text=True)[0]
    match = re.match(".+Bill Status for (.+)$",title_text)
    if match:
        return match.groups()[0]
    raise ValueError("Title text doesn't match expected pattern [%s]" % title_text)        
    
def get_all_bill_urls(scraper, chamber,session,types=None):
    """Given a session number (e.g. '96' for the 2009-2010 GA session) and a chamber,
       return all bill URLs which can be identified as associated with the given session.
       At this time, Executive Orders and Joint Session Resolutions will never be returned.
    """
    session_url = BASE_LEGISLATION_URL % session
    s = get_soup(scraper, session_url)
    groups = extract_bill_groups(s,session_url)
    special_sessions = s(text=re.compile(".*View Special Session.*"))
    if special_sessions:
        ss_url = urljoin(session_url,special_sessions[0].parent['href'])
        ss = get_soup(scraper, ss_url)
        groups.extend(extract_bill_groups(ss,ss_url))

    urls = []
    for g in groups:
        doctype = extract_doctype(g)
        if (types is None or doctype in types) and (chamber == chamber_for_doctype(doctype)):
            urls.extend(extract_bill_urls_from_group(scraper, chamber, g))
        
    return urls

def chamber_for_doctype(doctype):
    """
>>> chamber_for_doctype('EO')

>>> chamber_for_doctype('HB')
'lower'
>>> chamber_for_doctype('HJR')
'lower'
>>> chamber_for_doctype('HJRCA')
'lower'
>>> chamber_for_doctype('HR')
'lower'
>>> chamber_for_doctype('JSR')

>>> chamber_for_doctype('SB')
'upper'
>>> chamber_for_doctype('SJR')
'upper'
>>> chamber_for_doctype('SJRCA')
'upper'
>>> chamber_for_doctype('SR')
'upper'
    """
    if doctype.startswith("H"): return 'lower'
    if doctype.startswith("S"): return 'upper'
    return None
    
def extract_doctype(url):
    match = re.match(".*DocTypeID=(.+?)&.*",url)
    if match:
        return match.groups()[0]
    return None

def extract_session(url):
    match = re.match(".*GA=(\d+)&?.*",url)
    if match:
        return match.groups()[0]
    return None

def extract_bill_groups(soup,base_url=BASE_LEGISLATION_URL):
    """Given a BeautifulSoup instance, return the links within the parsed document which
    point to pages which list groups of bill status pages. The base_url is used to 
    qualify relative URLs.
    """
    links = soup("a", {"href": re.compile(".*grplist.*")})
    return map(lambda link: urljoin(base_url,link['href']),links)

def extract_bill_urls_from_group(scraper, chamber,url):
    """Given a url to a page grouping bills of a certain type in a certain session,
       return a sequence of all the URLs to the specific bill statuses from that page.
    """
    s = get_soup(scraper, url)
    bill_links = s("a",{"href":re.compile(".*BillStatus.*DocTypeID")})
    bill_links = map(lambda link: urljoin(url,link['href']), bill_links)
    return bill_links
