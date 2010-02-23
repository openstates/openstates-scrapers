#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import sys
from urllib2 import urlopen
from BeautifulSoup import BeautifulSoup 
from urlparse import urljoin, urlparse, urlunparse
import re
from urllib import urlencode
import os, os.path
import tempfile
from urllib import urlretrieve

import csv
from util import get_soup
from pyutils.legislation import Vote

EXPECTED_VOTE_CODES = ['Y','N','E','NV','A','P','-']
DOCUMENT_TYPES = ['EO', 'HB', 'HJR', 'HJRCA', 'HR', 'JSR', 'SB', 'SJR', 'SJRCA', 'SR']


VOTE_HISTORY_RELPATH = '/legislation/votehistory.asp'
BILL_STATUS_RELPATH = '/legislation/BillStatus.asp'

BASE_LEGISLATION_URL = "http://ilga.gov/legislation/default.asp"

VOTE_ACTION_PATTERN = re.compile("^(.+)(\d{3})-(\d{3})-(\d{3}).*$")

def get_pdf_content(path):
    """Return the text content of the PDF at the given path. Requires the pdftotext application be reachable.  
       If the given path begins with 'http' then the URL will be downloaded to a temp file.
       TODO: Cache PDFs?
    """
    if path.startswith("http"):
        f = tempfile.NamedTemporaryFile(suffix=".pdf")
        urlretrieve(path,f.name)
        path = f.name

    error_code = os.system("pdftotext -enc UTF-8 -layout %s" % path)
    if error_code:
        raise Exception("Error %i attempting to convert %s" % (error_code,path))
    txtpath = path[:-3] + "txt"
    return open(txtpath).readlines()

def get_bill_pages(url=None,doc_types=None):
    if url is None: url = legislation_url()
    """Return a sequence of tuples by retrieving all the documents described in the given url (representing
        a specific GA and session.)  Optionally filter the sequence to only the given document types ('house bill',
        'senate bill', etc.).  Each tuple returned will be in the form:
            (bill_id,short_name,status_url)
    """
    s = get_soup(url)
    links = s("a", { "href": lambda x: x is not None and x.find("grplist.asp") != -1 })
    links = map(lambda x: x['href'], links)
    d = {}
    for link in links:
        types = re.findall("DocTypeID=(.+?)&",link)
        for t in types:
            d.setdefault(t,[]).append(urljoin(url,link))

    pages = []
    if not doc_types:
        doc_types = ['HB','SB'] # sane default
    for type in doc_types:
        if d.has_key(type):
            simplified_url = min_max(d[type])
            pages.extend(extract_bill_links(simplified_url))
    
    return pages            

def min_max(l):
    """Given a list of document URLs, return a url which compresses them into one.
    """
    hi = 0
    low=100000000
    for url in l:
        match = re.match("^.+num1=(\d+)&.*num2=(\d+)&.+",url)
        if match:
            for num in match.groups():
                if int(num) < low: low = int(num)
                if int(num) > hi: hi = int(num)
                
    urlparts = urlparse(l[0])
    query = parse_qsl(urlparts.query)
    for (i,tup) in enumerate(query):
        if tup[0] == 'num1':
            query[i] = ('num1',low)
        elif tup[0] == 'num2':
            query[i] = ('num2',hi)
    urlparts = list(urlparts)
    urlparts[4] = urlencode(query)
    return urlunparse(urlparts)

def extract_bill_links(url):
    """Given a url to a page of BillStatus links (as expected from min_max),
       return a list of tuples of the form (id, title, url)
    """
    s = get_soup(url)
    links = s("a", { "href": lambda x: x is not None and x.find("BillStatus") != -1})
    l = []
    for link in links:
        text = link(text=True)[0].replace("&nbsp;"," ")
        match = re.match("^(\S+)\s+(.+)$",text)
        if match:
            l.append((match.groups()[0],match.groups()[1],urljoin(url,link['href'])))
    return l

def vote_history_link(url):
    """Assuming that everything about the URL should remain the same except for the server path,
       return a URL for the vote history.
       e.g. convert 
         http://ilga.gov/legislation/BillStatus.asp?DocNum=1&GAID=10&DocTypeID=HB&LegId=39979&SessionID=76&GA=96
       to
         http://ilga.gov/legislation/votehistory.asp?DocNum=1&GAID=10&DocTypeID=HB&LegId=39979&SessionID=76&GA=96
    """
    parts = list(urlparse(url))
    parts[2] = VOTE_HISTORY_RELPATH
    return urlunparse(parts)


def extract_vote_pdf_links(url,chamber_filter=None):
    """Given a URL to a "votehistory.asp" page, return a sequence of tuples, each of which 
       has the form (chamber,label,url)
       
       It's expected that the URLs are for PDF files.
    """
    l = []
    s = get_soup(url)
    if s.find(text="No vote detail available for the selected legislation."):
        return []
    tables = s("table")
    vote_table = tables[6]
    rows = vote_table("tr")
    rows = rows[1:] # lose header
    for row in rows:
        tds = row("td")
        if len(tds) > 1:
            c2 = tds[1]
            chamber = c2(text=True)[0]
            links = row("a")
            if links:
                link = links[0]
                href = urljoin(url,link['href'])
                label = link(text=True)[0]
                if (not chamber_filter) or chamber_filter.lower() == chamber.lower():
                    l.append((chamber,label,href))        
    return l        

def is_vote_line(line):
    for code in EXPECTED_VOTE_CODES:
        if line.startswith(code + " "): return True
    return False        

def _identify_candidate_columns(line):
    """Given a vote line, identify all columns in the line which contain valid vote codes.
       Result is returned as a set.
    """
    indices = set()
    for code in EXPECTED_VOTE_CODES:
        index = line.find(code + " ")
        while index != -1:
            indices.add(index)
            index = line.find(code,index + 1)
    return indices        

def mode(seq):
    max_count = None
    max_val = None
    for x in seq:
        if x is not max_val and seq.count(x) > max_count:
            max_count = seq.count(x)
            max_val = x
    return (max_val,max_count)

def _identify_columns(lines):
    """Given a sequence of vote lines, Identify the indices which in all rows contain legitimate known votes.
    """
    cols_seq = map(lambda line: _identify_candidate_columns(line), lines)
    (m,c) = mode(cols_seq)
    # mode is probably fine, but let's sanity check
    for cols in cols_seq:
        if len(cols) < len(m):
            if not cols.issubset(m):
                raise Exception("Shorter row can't align with expected column grid: [short: %s] [expected: %s]" % (cols,m))
        elif len(cols) > len(m):
            if not cols.issuperset(m):
                raise Exception("Longer row can't align with expected column grid: [long: %s] [expected: %s]" % (cols,m))
        # elif cols != m: # comment this out because it seems to get mucked up by unicode Muñoz
        #     raise Exception("Equal sized row doesn't match expected column grid: [equal: %s] [expected: %s]" % (cols,m))
    return tuple(m)
                
def is_vote_code_at(line,idx):
    for code in EXPECTED_VOTE_CODES:
        if line.find(code,idx) == idx: return True
    return False

def parse_vote_document(pdf_path):
    """
        Given the path to a PDF (such as might be retrieved from extract_vote_pdf_links), extract the votes and return as a dict with keys of voter names and values
        as codes like "Y", "N", "NV", "E", etc.  This is heavily dependent upon the columnar format 
        discovered experimentally.
    """
    if pdf_path.endswith(".txt"):
        lines = open(pdf_path).readlines()
    else:
        lines = get_pdf_content(pdf_path)
    votes = filter(is_vote_line,lines)
    column_indices = _identify_columns(votes)
    votedict = {}
    for voteline in votes:
        voteline = voteline.strip()
        linevotes = columnize(voteline,column_indices)
        for votefrag in linevotes:
            try:
                (vote,name) = votefrag.split(" ",1)
                votedict[name.strip()] = vote
            except ValueError:
                pass
                
    for (voter,vote) in votedict.iteritems():
        if vote not in EXPECTED_VOTE_CODES:
            raise Exception("Unexpected vote code %s by voter %s" % (vote,voter))
    return votedict

def columnize(line,indices):
    """Given a string and a sequence of index columns, cut the line into pieces where each begins at an index 
       and runs until just before the next index begins.  The sequence which is returned may have less items than there are indices, if it is shorter.
    """
    indices = list(indices)
    indices.sort()
    parts = []
    while indices:
        x,indices = indices[0],indices[1:]
        y = indices[0] if indices else len(line)
        part = line[x:y]
        if part: part = part.strip()
        parts.append(part)
    return parts
    
def _filename_from_url(url):
    parts = urlparse(url)
    path = parts[2]
    (path,filename) = os.path.split(path)
    return filename

def legislation_url(ga=None,session=None):
    query = {}
    if ga: query['GA'] = ga
    if session: query['SessionID'] = session
    url = BASE_LEGISLATION_URL
    if query:
        url += "?%s" % urlencode(query)
    return url

def _dump_votes_file_namer(voter,ga,session):
    output=re.sub("[^A-Za-z]","",voter)
    if ga: output += "_%s" % ga
    if session: output += "_%s" % session
    output += ".csv"
    return output

def all_votes_for_url(status_url):
    result = []
    votes = extract_vote_pdf_links(vote_history_link(status_url))        
    for (chamber,vote_desc,pdf_url) in votes:
        bill_votes = parse_vote_document(pdf_url)
        result.append((chamber,vote_desc,pdf_url,bill_votes))
    return result

def dump_votes(voter,chamber=None,ga=None,session=None,output=None):
    if voter is None:
        raise ValueError("A voter must be specified.")

    url = legislation_url(ga,session)
    pages = get_bill_pages(url)
    
    if output is None:
        output = _dump_votes_file_namer(voter,ga,session)                

    writer = csv.writer(open(output,"w"))
    writer.writerow(['bill_id','short_name','status_url','vote_desc','voters_vote','vote_pdf'])
    for (bill_id,short_name,status_url) in pages:
        votes = extract_vote_pdf_links(vote_history_link(status_url),chamber)
        for (chamber,vote_desc,pdf_url) in votes:
            bill_votes = parse_vote_document(pdf_url)
            voters_vote = bill_votes.get(voter,"VOTER %s NOT FOUND" % voter)
            writer.writerow([bill_id,short_name,status_url,vote_desc,voters_vote,pdf_url])

#---------------------
# parse_qsl lifted from Python 2.6 source:
def parse_qsl(qs, keep_blank_values=0, strict_parsing=0):
    """Parse a query given as a string argument.

    Arguments:

    qs: URL-encoded query string to be parsed

    keep_blank_values: flag indicating whether blank values in
        URL encoded queries should be treated as blank strings.  A
        true value indicates that blanks should be retained as blank
        strings.  The default false value indicates that blank values
        are to be ignored and treated as if they were  not included.

    strict_parsing: flag indicating what to do with parsing errors. If
        false (the default), errors are silently ignored. If true,
        errors raise a ValueError exception.

    Returns a list, as G-d intended.
    """
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r = []
    for name_value in pairs:
        if not name_value and not strict_parsing:
            continue
        nv = name_value.split('=', 1)
        if len(nv) != 2:
            if strict_parsing:
                raise ValueError, "bad query field: %r" % (name_value,)
            # Handle case of a control-name with no equal sign
            if keep_blank_values:
                nv.append('')
            else:
                continue
        if len(nv[1]) or keep_blank_values:
            name = unquote(nv[0].replace('+', ' '))
            value = unquote(nv[1].replace('+', ' '))
            r.append((name, value))

    return r

# and unquote lifted to support parse_qsl
_hextochr = dict(('%02x' % i, chr(i)) for i in range(256))
_hextochr.update(('%02X' % i, chr(i)) for i in range(256))

def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    res = s.split('%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return "".join(res)


#---------------------------
def main(argv=None):
    if argv is None:   
        argv = sys.argv

    print "nothing implemented yet!!!"
    

if __name__ == "__main__":
    sys.exit(main())
