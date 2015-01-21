import re
import os
import datetime
import collections
import json
from StringIO import StringIO

import requests
import scrapelib

from billy.scrape.utils import convert_pdf, PlaintextColumns
from billy.scrape.votes import Vote


class VoteParseError(Exception):
    pass


def parse_vote(scraper, chamber, doc_meta):
    # Get the pdf text.
    try:
        (path, resp) = scraper.urlretrieve(doc_meta.url)
    except scrapelib.HTTPError as exc:
        scraper.warning('Got error %r while fetching %s' % (exc, url))
        raise VoteParseError()
    text = convert_pdf(path, 'text')
    text = text.replace('\xc2\xa0', ' ')
    text = text.replace('\xc2\xad', ' ')
    os.remove(path)

    # Figure out what type of vote this is.
    if 'Roll Call' in text:
        return RollCallVote(text, scraper, chamber, doc_meta).vote()
    else:
        scraper.warning('Skipping a committee vote (See Jira issue DATA-80).')
        raise VoteParseError()


class RollCallVote(object):

    def __init__(self, text, scraper, chamber, doc_meta):
        self.text = text
        self.doc_meta = doc_meta
        self.url = doc_meta.url
        self.scraper = scraper
        self.chamber = chamber

    def date(self):
        try:
            date = re.search(r'[A-Z]+ \d{2}, \d{4}', self.text).group()
        except AttributeError:
            msg = "Couldn't find date on %s" % self.url
            self.scraper.logger.warning(msg)
            raise self.VoteParseError(msg)
        return datetime.datetime.strptime(date, "%b %d, %Y")

    def get_counts(self):
        return dict(re.findall(r'(Yeas?|Nays?|Excused|Not Voting)\s+(\d+)', self.text))

    def motion(self):
        return re.search('Roll Call \d+', self.text).group()

    def chamber(self):
        first_line = self.text.splitlines()[0]
        if 'House or Representatives' in first_line:
            return 'lower'
        else:
            return 'upper'

    def passed(self):
        result_types = {
            'FAILED': False,
            'DEFEATED': False,
            'PREVAILED': True,
            'PASSED': True,
            'SUSTAINED': True,
            'NOT SECONDED': False,
            'OVERRIDDEN': True,
            'ADOPTED': True,
        }
        text = self.text.upper()
        for key, value in result_types.items():
            if key in text:
                return value
        raise Exception("Couldn't determine vote passage status.")

    def vote_values(self):
        chunks = re.split(r'(YEA|NAY|EXCUSED|NOT VOTING)\s+\d+', self.text)[1:]
        data = dict(zip(chunks[::2], chunks[1::2]))
        votekeys = dict(YEA='yes', NAY='no')
        for key, data in data.items():
            garbage = re.split(r'(\s{4,}|\n)', data)
            for name in [name.strip() for name in garbage if name.strip()]:
                yield votekeys.get(key, 'other'), name

    def vote(self):
        '''Return a billy vote.
        '''
        actual_vote_dict = collections.defaultdict(list)
        date = self.date()
        motion = self.motion()
        passed = self.passed()
        counts = self.get_counts()
        yes_count = sum(int(counts.get(key, 0)) for key in ('Yea', 'Yeas'))
        no_count = sum(int(counts.get(key, 0)) for key in ('Nay', 'Nays'))
        vote = Vote(self.chamber, date, motion,
                    passed, yes_count, no_count,
                    sum(map(int, counts.values())) - (yes_count + no_count),
                    actual_vote=dict(actual_vote_dict))

        for vote_val, voter in self.vote_values():
            getattr(vote, vote_val)(voter)
        vote.add_source(self.url)
        return vote


# ----------------------------------------------------------------------------
# Handle documents hot mess.
# ----------------------------------------------------------------------------
class BogusDocument(Exception):
    pass


class DocumentMeta(object):
    DocMeta = collections.namedtuple('DocMeta', 'a,href,uid,title,text,url')

    def __init__(self, scraper, el):
        self.el = el
        self.scraper = scraper

    def get_doc_meta(self):
        text = self.el.text_content()
        text = re.sub(r'\s+', ' ', text).strip()
        api_meta = self.get_doc_api_meta(self.el.attrib)
        if api_meta is None:
            msg = 'No data recieved from the API for %r' % self.el.attrib
            raise BogusDocument(msg)
        static_url = self.get_document_url(api_meta)
        return self.DocMeta(
            a=self.el,
            text=text,
            href=self.el.attrib['href'],
            uid=self.el.attrib['data-myiga-actiondata'],
            title=self.el.attrib.get('title'),
            url=static_url)

    def get_doc_api_meta(self, attrib):
        '''The document link gives you json if you hit with the right
        Accept header.
        '''

        headers = dict(accept="application/json, text/javascript, */*")
        version_id = attrib['data-myiga-actiondata']
        if not version_id.strip():
            return
        if version_id in 'None':
            return
        png_url = 'http://iga.in.gov/documents/' + version_id

        self.scraper.logger.info('GET ' + png_url)
        try:
            resp = requests.get(png_url, headers=headers)
        except requests.exceptions.ConnectionError:
            self.warning('Connection error. Skipping doc metadata.')
            return
        try:
            data = resp.json()
        except:
            self.warning('Sigh. Skipping doc metadata.')
            return
        return data

    def get_document_url(self, data):
        '''If version_id is b5ff1c9c, the url will be:
        http://iga.in.gov/static-documents/b/5/f/f/b5ff1c9c/{data[name]}
        '''
        buf = StringIO()
        buf.write('http://iga.in.gov/static-documents/')
        for char in str(data['uid'])[:4]:
            buf.write(char)
            buf.write('/')
        buf.write(data['uid'])
        buf.write('/')
        buf.write(data['name'])
        return buf.getvalue()


class BillDocuments(object):
    '''The new IN site has lots of documents for each bill. Sorting them
    out from the kooky accordian view on the site is messy, so lives in
    this separate class.
    '''

    def __init__(self, scraper, bill_doc):
        self.doc = bill_doc
        self.scraper = scraper

    def guess_doc_type(self, meta):
        '''Guess whether this is a version, document, report,
        or roll call vote.
        '''
        title = (meta.title or meta.text).lower()
        if 'bill' in title:
            return 'version'
        if 'roll call' in title:
            return 'rollcall'

        textbits = meta.text.split('.')
        lastbit = textbits[-1]
        # Fiscal note, amendment, committee report
        if lastbit.startswith(('FN', 'AMS', 'CR')):
            return 'document'

    def iter_doc_meta(self):
        xpath = '//*[@data-myiga-actiondata]'
        meta = []
        for a in self.doc.xpath(xpath):
            try:
                data = DocumentMeta(self.scraper, a).get_doc_meta()
            except BogusDocument as exc:
                self.scraper.logger.warning(exc)
                self.scraper.logger.warning('Skipping document: %r.' % (a.attrib,))
                continue
            meta.append(data)
        return meta

    def get_deduped_meta(self):
        meta = list(self.iter_doc_meta())
        grouped = collections.defaultdict(set)
        for data in meta:
            grouped[data.uid].add(data)
        for k, v in grouped.items():
            if 1 < len(v):
                for data in list(v):
                    if not data.text:
                        v.remove(data)
                    if not v:
                        v.add(data)
        for k, v in grouped.items():
            yield v.pop()

    def __iter__(self):
        for data in self.get_deduped_meta():
            yield self.guess_doc_type(data), data
