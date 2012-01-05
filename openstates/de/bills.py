'''
01/03/2012 - Changed link-gathering function to get resolutions, etc.
'''
import re
import pdb
import urllib
from urlparse import urlparse
from datetime import datetime
from operator import methodcaller

import lxml.html
from functional import partial

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import scrapelib


class UnidentifiedActorError(ScrapeError):
    '''
    Raised when function `get_action_actor` fails to guess any actor
    for a particular action.
    '''
    pass


class BillIdParseError(ScrapeError):
    '''
    Raised when function `parse_bill_id` returns a string that
    doesn't remotely resmble a valid bill_id.
    '''
    pass


def get_text(doc, i, xpath):
    '''
    A shortcut to get stripped text content given 1) a document of
    type lxml.html.HtmlElement, 2) an xpath, and 3) optionaly
    an index `i` that defaults to zero. 
    '''
    if not i:
        i = 0
    return doc.xpath(xpath)[i].text_content().strip()


def slugify(s):
    '''
    Turn a phrase like "Current Status:" into "current_status".
    '''
    return s.lower().replace(' ', '_').rstrip(':')


def get_action_actor(action_text, rgxs=(
    (re.compile(r'(in|by) senate', re.I), 'upper'),
    (re.compile(r'(in|by) house', re.I), 'lower'),
    (re.compile(r'by governor', re.I), 'governor'),
    )):
    '''
    Guess the actor for a particular action.
    '''
    for r, actor in rgxs:
        m = r.search(action_text)
        if m:
            return actor
    msg = 'Couldn\'t identify the actor for action: "%s"'
    raise UnidentifiedActorError(msg % action_text)

        
def get_action_type(action_text):
    '''
    Apply an action type to an action.
    '''

def parse_votestring(v, strptime=datetime.strptime,
    re_date = re.compile('\d{,2}/\d{,2}/\d{,4} [\d:]{,8} [AP]M'),
    chambers={'House': 'lower', 'Senate': 'upper'}):
    '''
    Parse contents of the string on the main bill detail page
    describing a vote.
    '''
    motion, _ = v.split(':', 1)
    
    date = strptime(re_date.search(v).group(), '%m/%d/%Y %I:%M:%S %p')

    chamber, _ = v.split(' ', 1)
    chamber = chambers[chamber]
    
    passed = ('Passed' in v)

    return dict(date=date, chamber=chamber, passed=passed, motion=motion)


def extract_bill_id(bill_id, fns=(
    partial(re.compile(r' w/.A \d{1,3}.{,20}$').sub, ''),
    partial(re.compile(r'^.{,20}for ').sub, '')),
    is_valid=re.compile(r'[A-Z]{2,4} \d{1,6}$').match):
    '''
    Given a bill id string from the website's index pages, removes
    characters indicating amendments and substitutions, e.g.:

        SB 137 w/SA 1 --> SB 137
        SB 112 w/SA 1 + HA 1 --> SB 112
        SS 1 for SB 156 --> SB 156

    Complains if the result doesn't look like a normla bill id.
    '''
    for f in fns:
        bill_id = f(bill_id)

    if not is_valid(bill_id):
        raise 

    return bill_id
            


class DEBillScraper(BillScraper):
    '''
    Scrapes bills for the current session. Delware's website
    (http://legis.delaware.gov/) lists archival data separately and
    with a different (though similar) format.
    See http://legis.delaware.gov/LEGISLATURE.NSF/LookUp/LIS_archives?opendocument
    '''
    
    state = 'de'

    legislation_types = {
        'House Bill': 'bill',
        'House Concurrent Resolution': 'concurrent resolution',
        'House Joint Resolution': 'joint resolution',
        'House Resolution': 'resolution',
        'Senate Bill': 'bill',
        'Senate Concurrent Resolution': 'concurrent resolution',
        'Senate Joint Resolution': 'joint resolution',
        'Senate Resolution': 'resolution',
        'Senate Nominations': 'nomination',
        }

    def _url_2_lxml(self, url, encoding='ascii',
                    base_url='{0.scheme}://{0.netloc}'.format):
        '''
        Fetch the url as a string, convert it to unicode,
        and parse with lxml.
        '''
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html.decode(encoding))
        urldata = urlparse(url)
        doc.make_links_absolute(base_url(urldata))
        return doc

    def _cleanup_sponsors(self, string, chamber,

        # Splits at ' & '                  
        re_amp=re.compile(r'\s{,5}[,&]\s{1,5}'),

        # Changes "Sen. Jones" into "Jones"
        re_title=re.compile(r'(Sen|Rep)s?\.\s'),

        # Map to clean up sponsor name data.
        name_map={
            '{ NONE...}': '',
            },

        # Mapping of member designations to related chamber type.
        chamber_map={
            'Sen': 'upper',
            'Rep': 'lower',
            }

        ):
        
        '''
        Sponsor names are sometimes joined with an ampersand,
        are '{ NONE...}', or contain '&nbsp'. This helper removes
        that stuff and returns a list minus any non-name strings found. 
        '''
        res = []
        
        for string in string.split('; '):

            # Override the chamber based on presence of "Sens." or "Rep."
            m = re_title.search(string)
            if m:
                chamber = chamber_map[m.group(1)]

            # Remove junk.    
            names = re_amp.split(string)
            names = map(lambda s: re_title.sub('', s), names)
            names = map(methodcaller('replace', '&nbsp', ''), names)
            names  = filter(None, [name_map.get(n, n) for n in names])

            res += [(n, chamber) for n in names]

        return res
    
    def _get_urls(self, chamber, session):
        '''
        A generator of urls to legislation types listed on the
        index_url page.
        '''
        re_count = re.compile(r'count=\d+')
        
        index_url = ('http://legis.delaware.gov/LIS/lis146.nsf'
                     '/Legislation/?openview')

        chamber_map = {'s': 'upper',
                       'a': 'lower'}

        legislation_types = self.legislation_types
        
        index_page = self._url_2_lxml(index_url)      

        for el in index_page.xpath('//a[contains(@href, "Expand=")]'):

            type_ = el.xpath('../following-sibling::td')[0].text_content()
            type_ = legislation_types[type_]

            # Skip any links that aren't for this chamber.
            el_text = el.text_content()
            if el_text and chamber_map[el_text[0].lower()] != chamber:
                continue

            # Tweak the url to ask the server for 10000 results (i.e., all)
            url = el.attrib['href']
            url = re_count.sub('count=10000', url)

            # Get the index page.
            doc = self._url_2_lxml(url)

            # Parse urls and bill kwargs for listed legislation.
            for el in doc.xpath('//a[contains(@href, "OpenDocument")]'):
                
                title = el.xpath('./../../../td[4]')[0].text_content()

                url = el.attrib['href']
                
                bill_kwargs = {'type': type_,
                               'bill_id': extract_bill_id(el.text),
                               'chamber': chamber,
                               'session': session,
                               'title': title}
                
                yield (url, bill_kwargs)


    def scrape(self, chamber, session):     

        scrape_bill = self.scrape_bill
        for url, kw in self._get_urls(chamber, session):
            scrape_bill(url, kw)
            

    def scrape_bill(self, url, kw,        
                    re_docnum=re.compile(r'var docnum="(.+?)"'),
                    re_moniker=re.compile(r'var moniker="(.+?)"'),
                    re_digits=re.compile(r'\d{,5}'),
                    re_amendment=re.compile(r'(^[A-Z]A \d{1,3}) to'),
                    re_substitution=re.compile(r'(^[A-Z]S \d{1,2}) for')):

        url = 'http://legis.delaware.gov/LIS/lis146.nsf/2bede841c6272c888025698400433a04/60ea60e782adddf5852578b10062fe03?OpenDocument'
            
        bill = Bill(**kw)
        
        bill.add_source(url)


        #---------------------------------------------------------------------
        # A few helpers.
        
        _url_2_lxml = self._url_2_lxml
        _cleanup_sponsors = self._cleanup_sponsors

        # Shortcut function partial to get text at a particular xpath:
        doc = _url_2_lxml(url)
        _get_text = partial(get_text, doc, 0)


        #---------------------------------------------------------------------
        # Sponsors

        chamber = bill['chamber']
        
        sponsor_types = {
            'Additional Sponsor(s):': 'other',
            'CoSponsors:': 'cosponsor',
            'Primary Sponsor:': 'primary'}

        xpath = '//font[contains(., "Sponsor") and @color="#008080"]'
        headings = doc.xpath(xpath + '/text()')
        sponsors = doc.xpath(xpath + '/../../following-sibling::td/font/text()')

        for h, s in zip(headings, sponsors):

            names = _cleanup_sponsors(s, chamber)
            type_ = sponsor_types[h.strip()]

            if names:
                for name, _chamber in names:
                    bill.add_sponsor(type_, name, chamber=_chamber)

        
        #---------------------------------------------------------------------
        # Versions

        # The full-text urls are generated using onlick javascript and
        # window-level vars named "moniker" and "docnum". 
        script_text = _get_text('//script[contains(., "var docnum")]')
        docnum = re_docnum.search(script_text).group(1)
        moniker = re_moniker.search(script_text).group(1)

        # Get session number.
        session_num = _get_text('//font[contains(., "General Assembly") and @face="Arial"]')
        session_num = re_digits.match(session_num).group()

        tmp = '/'.join(['http://www.legis.delaware.gov',
                        'LIS/lis%s.nsf/vwLegislation' % session_num,
                        moniker, '$file/%s%s?open'])

        formats = ['.html', '.pdf', '.docx']

        for f in formats:

            if not doc.xpath('//font[contains(., "Legis%s")]' % f):
                continue

            if f == '.docx':
                vals = (docnum, f)
                
            else:
                vals = ('Legis', f)

            url = tmp % vals

            try:
                self.urlopen(url)
                
            except scrapelib.HTTPError:
                msg = 'Could\'t fetch %s version at url: "%s".'
                self.warning(msg % (f, url))
                
            else:
                bill.add_version('introduced', url, format=f)


        # If bill is a substitution, add the original as a version.
        names = doc.xpath('//*[contains(text(), "Substituted '
                          'Legislation for Bill:")]/text()')
        urls = doc.xpath('//*[contains(text(), "Substituted '
                          'Legislation for Bill:")]'
                         '/following-sibling::a/@href')
        
        for name, url in zip(names, urls):

            name = re_substitution.match(name).group(1)
            bill.add_version(name, url,
                             description='original bill')

        #---------------------------------------------------------------------
        # Actions
        actions = doc.xpath('//font[contains(., "Actions History")]'
                            '/../following-sibling::table/descendant::td[2]')
        actions = actions[0].text_content()
        actions = filter(None, actions.splitlines())

        for a in actions:
            date, action = a.split(' - ', 1)
            date = datetime.strptime(date, '%b %d, %Y')
            actor = get_action_actor(action)
            type_ = get_action_type(action)
            bill.add_action(actor, action, date, type_)

        
        #---------------------------------------------------------------------
        # Votes
        
        vote_strings = doc.xpath('//*[contains(text(), "vote:")]/text()')
        vote_urls = doc.xpath('//*[contains(text(), "vote:")]'
                              '/following-sibling::a/@href')
        for string, url in zip(vote_strings, vote_urls):
            
            vote_data = parse_votestring(string)
            vote = self.scrape_vote(url, **vote_data)
            bill.add_vote(vote)

        #---------------------------------------------------------------------
        # Amendments

        xpath = ("//font[contains(., 'Amendments')]/"
                 "../../../td[2]/font/a")
        
        for url, id_ in zip(doc.xpath(xpath + '/@href'),
                            doc.xpath(xpath + '/text()')):

            id_ = re_amendment.match(id_).group(1)
            
            _kw = kw.copy()
            _kw.update(bill_id=id_)

            # Silly geese. No spaces allowed in urls...
            url = url.replace(' ', '+')

            bill.add_document(id_, url, _type='amendment')


        #---------------------------------------------------------------------
        # Add any related "Engrossments".
        # See www.ncsl.org/documents/legismgt/ILP/98Tab3Pt4.pdf for
        # an explanation of the engrossment process in DE.

        pdb.set_trace()
        url = doc.xpath('//img[@alt="Engrossment"]/../@href')[0]
        if url:
            _doc = _url_2_lxml(url)
            
            script_text = get_text(_doc, 0, '//script[contains(., "var docnum")]')
            docnum = re_docnum.search(script_text).group(1)
            moniker = re_moniker.search(script_text).group(1)

            tmp = '/'.join(['http://www.legis.delaware.gov',
                            'LIS/lis%s.nsf/EngrossmentsforLookup' % session_num,
                            moniker, '$file/%s%s?open'])

            formats = ['.html', '.pdf', '.docx']

            for f in formats:

                if not _doc.xpath('//font[contains(., "Engross%s")]' % f):
                    continue

                if f == '.docx':
                    vals = (docnum, f)
                    
                else:
                    vals = ('Engross', f)

                url = tmp % vals

                try:
                    self.urlopen(url)
                    
                except scrapelib.HTTPError:
                    msg = 'Could\'t fetch %s version at url: "%s".'
                    self.warning(msg % (f, url))
                    
                else:
                    bill.add_document('engrossment', url, format=f)

        #---------------------------------------------------------------------
        # Extra fields

        # Helper to get the first td sibling of certain nodes.
        tmp = '//font[contains(., "%s")]/../../../td[2]'
        first_sibling_text = lambda heading: _get_text(tmp % heading)

        extra_fields = (

            # A long description of the legislation.
            "Synopsis",

            # Codification details for enacted legislation.
            "Volume Chapter",

            # Presumably the date of approval/veto.
            "Date Governor Acted"

            )

        for f in extra_fields:
            
            try:
                bill[slugify(f)] = first_sibling_text(f)
                
            except IndexError:
                # xpath lookup failed.
                pass


        pdb.set_trace()


    def scrape_vote(self, url, date, chamber, passed, motion,
                    re_digit=re.compile(r'\d{1,3}')):

        namespaces = {"re": "http://exslt.org/regular-expressions"}
        doc = lxml.html.fromstring(self.urlopen(url))

        xpath = ("//font[re:match(., '^(Yes|No|Not Voting|Absent):', 'i')]"
              "/ancestor::tr[1]")

        # Get the vote tallies.
        totals = doc.xpath(xpath, namespaces=namespaces)[0].text_content()
        totals = re_digit.findall(totals)

        yes_count, no_count, abstentions, absent = map(int, totals)
        other_count = abstentions + absent

        # Create the vote object.
        vote = Vote(chamber, date, motion, passed,
                    yes_count, no_count, other_count)

        # Add source.
        vote.add_source(url)

        # Get an iterator like: name1, vote1, name2, vote2, ...
        xpath = ("//font[re:match(., '^[A-Z]$')]"
              "/../../../descendant::td/font/text()")
        data = doc.xpath(xpath, namespaces=namespaces)
        data = iter(filter(lambda s: s.strip(), data))

        # Add names and vote values.
        vote_map = {
            'Y': 'yes',
            'N': 'no'
            }

        while True:
            
            try:
                name = data.next()
                vote_ = vote_map.get(data.next(), 'other')
                getattr(vote, vote_)(name)
                
            except StopIteration:
                break

        return vote

    def scrape_amendment(self, url, kw):
        '''
        Add another bill object for the amendment at this url.
        '''

        doc = self._url_2_lxml(url)

        title = doc.xpath('//font[contains(., "AMENDMENT NO:")]')
        pdb.set_trace()
        
        bill = Bill(**kw)
        
        bill.add_source(url)

        pdb.set_trace()
