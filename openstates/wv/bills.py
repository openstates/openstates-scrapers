
import os
import re
import datetime
import collections
from urlparse import urlparse, parse_qsl
from urllib import quote, unquote_plus

import lxml.html

from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import scrapelib

from .actions import Categorizer


class _Url(object):
    '''A url object that can be compared with other url orbjects
    without regard to the vagaries of casing, encoding, escaping,
    and ordering of parameters in query strings.'''

    def __init__(self, url):
        parts = urlparse(url.lower())
        _query = frozenset(parse_qsl(parts.query))
        _path = unquote_plus(parts.path)
        parts = parts._replace(query=_query, path=_path)
        self.parts = parts

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


class WVBillScraper(BillScraper):
    jurisdiction = 'wv'
    categorizer = Categorizer()

    bill_types = {'B': 'bill',
                  'R': 'resolution',
                  'CR': 'concurrent resolution',
                  'JR': 'joint resolution'}

    def scrape(self, chamber, session):
        if chamber == 'lower':
            orig = 'h'
        else:
            orig = 's'

        # scrape bills
        if (self.metadata['session_details'][session]['type'] == 'special'):
            url = ("http://www.legis.state.wv.us/Bill_Status/"
               "Bills_all_bills.cfm?year=%s&sessiontype=%s"
               "&btype=bill&orig=%s" 
               % (self.metadata['session_details'][session]['_scraped_name'],
               self.metadata['session_details'][session]['_special_name'],
               orig))
        else:
            url = ("http://www.legis.state.wv.us/Bill_Status/"
               "Bills_all_bills.cfm?year=%s&sessiontype=RS"
               "&btype=bill&orig=%s" % (session, orig))
               
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Bills_history')]"):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            if not title:
                self.logger.warning("Can't find bill title, using ID as title")
                title = bill_id
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])

        # scrape resolutions
        if (self.metadata['session_details'][session]['type'] == 'special'):
            res_url = ("http://www.legis.state.wv.us/Bill_Status/res_list.cfm?year=%s&sessiontype=%s&btype=res" 
                % (self.metadata['session_details'][session]['_scraped_name'], 
                self.metadata['session_details'][session]['_special_name']))
        else:
            res_url = ("http://www.legis.state.wv.us/Bill_Status/res_list.cfm?year=%s&sessiontype=rs&btype=res" 
                   % (self.metadata['session_details'][session]['_scraped_name']))
                   
        doc = lxml.html.fromstring(self.get(res_url).text)
        doc.make_links_absolute(res_url)

        # check for links originating in this house
        for link in doc.xpath('//a[contains(@href, "houseorig=%s")]' % orig):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            if not title:
                self.logger.warning("Can't find bill title, using ID as title")
                title = bill_id
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])

    def scrape_bill(self, session, chamber, bill_id, title, url,
                    strip_sponsors=re.compile(r'\s*\(.{,50}\)\s*').sub):

        html = self.get(url).text

        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        bill_type = self.bill_types[bill_id.split()[0][1:]]

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)

        xpath = ('//strong[contains(., "SUBJECT")]/../'
                 'following-sibling::td/a/text()')
        bill['subjects'] = page.xpath(xpath)

        for version in self.scrape_versions(session, chamber, page, bill_id):
            bill.add_version(**version)

        # Resolution pages have different html.
        values = {}
        trs = page.xpath('//div[@id="bhistcontent"]/table/tr')
        for tr in trs:
            heading = tr.xpath('td/strong/text()')
            if heading:
                heading = heading[0]
            else:
                continue
            value = tr.text_content().replace(heading, '').strip()
            values[heading] = value

        # summary was always same as title
        #bill['summary'] = values['SUMMARY:']

        # Add primary sponsor.
        primary = strip_sponsors('', values.get('LEAD SPONSOR:', ''))
        if primary:
            bill.add_sponsor('primary', primary)

        # Add cosponsors.
        if values.get('SPONSORS:'):
            sponsors = strip_sponsors('', values['SPONSORS:'])
            sponsors = re.split(', (?![A-Z]\.)', sponsors)
            for name in sponsors:
                name = name.strip(', \n\r')
                if name:
                    # Fix name splitting bug where "Neale, D. Hall"
                    match = re.search('(.+?), ([DM]\. Hall)', name)
                    if match:
                        for name in match.groups():
                            bill.add_sponsor('cosponsor', name)
                    else:
                        bill.add_sponsor('cosponsor', name)

        for link in page.xpath("//a[contains(@href, 'votes/house')]"):
            self.scrape_house_vote(bill, link.attrib['href'])

        for tr in reversed(page.xpath("//table[@class='tabborder']/descendant::tr")[1:]):
            tds = tr.xpath('td')
            if len(tds) < 3:
                continue

            chamber_letter = tds[0].text_content()
            chamber = {'S': 'upper', 'H': 'lower'}[chamber_letter]

            # Index of date info no longer varies on resolutions.
            date = tds[2].text_content().strip()
            date = datetime.datetime.strptime(date, "%m/%d/%y").date()

            action = tds[1].text_content().strip()
            if action.lower().startswith('passed senate'):
                for href in tds[1].xpath('a/@href'):
                    self.scrape_senate_vote(bill, href, date)

            attrs = dict(actor=chamber, action=action, date=date)
            attrs.update(self.categorizer.categorize(action))
            bill.add_action(**attrs)

        self.save_bill(bill)

    def scrape_house_vote(self, bill, url):
        try:
            filename, resp = self.urlretrieve(url)
        except scrapelib.HTTPError:
            self.warning("missing vote file %s" % url)
            return
        text = convert_pdf(filename, 'text')
        os.remove(filename)

        lines = text.splitlines()

        vote_type = None
        votes = collections.defaultdict(list)

        for idx, line in enumerate(lines):
            line = line.rstrip()
            match = re.search(r'(\d+)/(\d+)/(\d{4,4})$', line)
            if match:
                date = datetime.datetime.strptime(match.group(0), "%m/%d/%Y")
                continue

            match = re.match(
                r'\s+YEAS: (\d+)\s+NAYS: (\d+)\s+NOT VOTING: (\d+)',
                line)
            if match:
                motion = lines[idx - 2].strip()
                if not motion:
                    self.warning("No motion text found for vote")
                    motion = "PASSAGE"
                yes_count, no_count, other_count = [
                    int(g) for g in match.groups()]

                exc_match = re.search(r'EXCUSED: (\d+)', line)
                if exc_match:
                    other_count += int(exc_match.group(1))

                if line.endswith('ADOPTED') or line.endswith('PASSED'):
                    passed = True
                else:
                    passed = False

                continue

            match = re.match(
                r'(YEAS|NAYS|NOT VOTING|PAIRED|EXCUSED):\s+(\d+)\s*$',
                line)
            if match:
                vote_type = {'YEAS': 'yes',
                             'NAYS': 'no',
                             'NOT VOTING': 'other',
                             'EXCUSED': 'other',
                             'PAIRED': 'paired'}[match.group(1)]
                continue

            if vote_type == 'paired':
                for part in line.split('   '):
                    part = part.strip()
                    if not part:
                        continue
                    name, pair_type = re.match(
                        r'([^\(]+)\((YEA|NAY)\)', line).groups()
                    name = name.strip()
                    if pair_type == 'YEA':
                        votes['yes'].append(name)
                    elif pair_type == 'NAY':
                        votes['no'].append(name)
            elif vote_type:
                for name in line.split('   '):
                    name = name.strip()
                    if not name:
                        continue
                    votes[vote_type].append(name)

        vote = Vote('lower', date, motion, passed,
                    yes_count, no_count, other_count)
        vote.add_source(url)

        vote['yes_votes'] = votes['yes']
        vote['no_votes'] = votes['no']
        vote['other_votes'] = votes['other']

        assert len(vote['yes_votes']) == yes_count
        assert len(vote['no_votes']) == no_count
        assert len(vote['other_votes']) == other_count

        bill.add_vote(vote)

    def scrape_senate_vote(self, bill, url, date):
        try:
            filename, resp = self.urlretrieve(url)
        except scrapelib.HTTPError:
            self.warning("missing vote file %s" % url)
            return

        vote = Vote('upper', date, 'Passage', passed=None,
                    yes_count=0, no_count=0, other_count=0)
        vote.add_source(url)

        text = convert_pdf(filename, 'text')
        os.remove(filename)

        if re.search('Yea:\s+\d+\s+Nay:\s+\d+\s+Absent:\s+\d+', text):
            return self.scrape_senate_vote_3col(bill, vote, text, url, date)

        data = re.split(r'(Yea|Nay|Absent)s?:', text)[::-1]
        data = filter(None, data)
        keymap = dict(yea='yes', nay='no')
        actual_vote = collections.defaultdict(int)
        while True:
            if not data:
                break
            vote_val = data.pop()
            key = keymap.get(vote_val.lower(), 'other')
            values = data.pop()
            for name in re.split(r'(?:[\s,]+and\s|[\s,]{2,})', values):
                if name.lower().strip() == 'none.':
                    continue
                name = name.replace('..', '')
                name = re.sub(r'\.$', '', name)
                name = name.strip('-1234567890 \n')
                if not name:
                    continue
                getattr(vote, key)(name)
                actual_vote[vote_val] += 1
                vote[key + '_count'] += 1
            assert actual_vote[vote_val] == vote[key + '_count']

        vote['passed'] = vote['no_count'] < vote['yes_count']
        bill.add_vote(vote)

    def scrape_senate_vote_3col(self, bill, vote, text, url, date):
        '''Scrape senate votes like this one:
        http://www.legis.state.wv.us/legisdocs/2013/RS/votes/senate/02-26-0001.pdf
        '''
        counts = dict(re.findall(r'(Yea|Nay|Absent): (\d+)', text))
        lines = filter(None, text.splitlines())
        actual_vote = collections.defaultdict(int)
        for line in lines:
            vals = re.findall(r'(?<!\w)(Y|N|A)\s+((?:\S+ ?)+)', line)
            for vote_val, name in vals:
                vote_val = vote_val.strip()
                name = name.strip()
                if vote_val == 'Y':
                    vote.yes(name)
                    vote['yes_count'] += 1
                elif vote_val == 'N':
                    vote.no(name)
                    vote['no_count'] += 1
                else:
                    vote.other(name)
                    vote['other_count'] += 1
                actual_vote[vote_val] += 1

        vote['passed'] = vote['no_count'] < vote['yes_count']

        assert vote['yes_count'] == int(counts['Yea'])
        assert vote['no_count'] == int(counts['Nay'])
        assert vote['other_count'] == int(counts['Absent'])
        bill.add_vote(vote)

    def _scrape_versions_normally(self, session, chamber, page, bill_id,
                                  get_name=re.compile(r'\"(.+)"').search):
        '''This first method assumes the bills versions are hyperlinked
        on the bill's status page.
        '''
        for link in page.xpath("//a[starts-with(@title, 'HTML -')]"):
            # split name out of HTML - Introduced Version - SB 1
            name = link.xpath('@title')[0].split('-')[1].strip()
            yield {'name': name, 'url': link.get('href'),
                   'mimetype': 'text/html'}

    def scrape_versions(self, session, chamber, page, bill_id):
        '''
        Return all available version documents for this bill_id.
        '''
        res = []
        cache = set()

        # Scrape .htm and .wpd versions listed in the detail page.
        for data in self._scrape_versions_normally(session, chamber, page,
                                                   bill_id):
            _url = _Url(data['url'])
            if _url not in cache:
                cache.add(_url)
                res.append(data)

        return res
