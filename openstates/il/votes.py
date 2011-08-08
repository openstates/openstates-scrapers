# -*- coding: utf-8 -*-
from urlparse import urljoin, urlparse, urlunparse
import re

from billy.scrape.votes import Vote

EXPECTED_VOTE_CODES = ['Y','N','E','NV','A','P','-']
VOTE_HISTORY_RELPATH = '/legislation/votehistory.asp'


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


def extract_vote_pdf_links(scraper, url,chamber_filter=None):
    """Given a URL to a "votehistory.asp" page, return a sequence of tuples, each of which
       has the form (chamber,label,url)

       It's expected that the URLs are for PDF files.
    """
    l = []
    s = get_soup(scraper, url)
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


def all_votes_for_url(scraper, status_url):
    result = []
    votes = extract_vote_pdf_links(scraper, vote_history_link(status_url))
    for (chamber,vote_desc,pdf_url) in votes:
        bill_votes = parse_vote_document(pdf_url)
        result.append((chamber,vote_desc,pdf_url,bill_votes))
    return result
