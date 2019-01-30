import os
import re
import operator
from datetime import datetime
from bisect import bisect_left

import lxml.html
import lxml.etree
import scrapelib

from pupa.scrape import Scraper, VoteEvent
from pupa.utils.generic import convert_pdf

# Senate vote header
s_vote_header = re.compile(r'(YES)|(NO)|(ABS)|(EXC)|(REC)')
# House vote header
h_vote_header = re.compile(
    r'(YEA(?!S))|(NAY(?!S))|(EXCUSED(?!:))|(ABSENT(?!:))')

# Date regex for senate and house parser
date_regex = re.compile(r'([0-1][0-9]/[0-3][0-9]/\d+)')


def convert_sv_char(c):
    """ logic for shifting senate vote characters to real ASCII """
    # capital letters shift 64
    if 65 <= ord(c) - 64 <= 90:
        return chr(ord(c) - 64)
    # punctuation shift 128
    else:
        try:
            return chr(ord(c) - 128)
        except ValueError:
            return c


def match_header(row_cols, cell_x):
    """ Map the data column to the header column, has to be done once for each
        column. The columns of the headers(yes/no/etc) do not mach up *perfect*
        with data in the grid due to random preceding whitespace and mixed
        fonts"""
    row_cols.sort()
    c = bisect_left(row_cols, cell_x)
    if c == 0:
        return row_cols[0]
    elif c == len(row_cols):
        return row_cols[-1]

    before = row_cols[c - 1]
    after = row_cols[c]
    if after-cell_x < cell_x-before:
        return after
    else:
        return before


def session_slug(session):
    session_type = 'Special' if session.endswith('S') else 'Regular'
    return '{}%20{}'.format(session[2:4], session_type)


# Fix names that don't get read correctly from the vote PDFs
corrected_names = {'Larraqaga': 'Larrañaga',
                   'Salazar, Tomas': 'Salazar, Tomás',
                   'Sariqana': 'Sariñana',
                   'MUQOZ': 'MUÑOZ'}


def correct_name(name):
    return corrected_names[name] if name in corrected_names else name


def build_vote(session, bill_id, url, vote_record, chamber, motion_text):
    passed = len(vote_record['yes']) > len(vote_record['no'])
    vote_event = VoteEvent(
        result='pass' if passed else 'fail',
        chamber=chamber,
        start_date=vote_record['date'].strftime('%Y-%m-%d'),
        motion_text=motion_text,
        classification='passage',
        legislative_session=session,
        bill=bill_id,
        bill_chamber='upper' if bill_id[0] == 'S' else 'lower'
    )
    vote_event.pupa_id = url
    vote_event.set_count('yes', len(vote_record['yes']))
    vote_event.set_count('no', len(vote_record['no']))
    vote_event.set_count('excused', len(vote_record['excused']))
    vote_event.set_count('absent', len(vote_record['absent']))
    vote_event.set_count('other', len(vote_record['other']))
    for vote_type in ['yes', 'no', 'excused', 'absent', 'other']:
        for voter in vote_record[vote_type]:
            vote_event.vote(vote_type, voter)

    vote_event.add_source(url)
    return vote_event


def validate_house_vote(row_headers, sane_row, vote_record):
    # Sanity checks on vote data, checks that the calculated total and
    # listed totals match
    sane = {'yes': 0, 'no': 0, 'excused': 0, 'absent': 0, 'other': 0}
    # Make sure the header row and sanity row are in order
    sorted_row_header = sorted(row_headers.items(),
                               key=operator.itemgetter(0))
    start_count = -1
    for cell in sane_row:
        cell_value = cell[0].split()[-1].strip()
        if 'YEAS' in cell[0] or start_count >= 0:
            start_count += 1
            sane_vote = sorted_row_header[start_count][1]
            if 'Y' == sane_vote[0]:
                sane['yes'] = int(cell_value)
            elif 'N' == sane_vote[0]:
                sane['no'] = int(cell_value)
            elif 'E' == sane_vote[0]:
                sane['excused'] = int(cell_value)
            elif 'A' == sane_vote[0]:
                sane['absent'] = int(cell_value)
            else:
                sane['other'] += int(cell_value)
    # Make sure the parsed vote totals match up with counts in the total
    # field
    if not sane_matches_captured(sane, vote_record):
        raise ValueError('Votes were not parsed correctly')


def validate_senate_vote(row_headers, sane_row, vote_record):
    # Sanity checks on vote data, checks that the calculated total and
    # listed totals match
    sane = {'yes': 0, 'no': 0, 'excused': 0, 'absent': 0, 'other': 0}
    # Make sure the header row and sanity row are in order
    sorted_row_header = sorted(row_headers.items(),
                               key=operator.itemgetter(0))
    start_count = -1
    for cell in sane_row:
        cell_value = cell[0]
        if start_count >= 0:
            sane_vote = sorted_row_header[start_count][1]
            if 'Y' == sane_vote[0]:
                sane['yes'] = int(cell_value)
            elif 'N' == sane_vote[0]:
                sane['no'] = int(cell_value)
            elif 'E' == sane_vote[0]:
                sane['excused'] = int(cell_value)
            elif 'A' == sane_vote[0]:
                sane['absent'] = int(cell_value)
            else:
                sane['other'] += int(cell_value)
            start_count += 1
        elif 'TOTAL' in cell_value:
            start_count = 0
    # Make sure the parsed vote totals match up with counts in the
    # total field
    if not sane_matches_captured(sane, vote_record):
        raise ValueError('Votes were not parsed correctly')


def sane_matches_captured(sane, vote_record):
    return sane['yes'] == len(vote_record['yes']) and \
           sane['no'] == len(vote_record['no']) and \
           sane['excused'] == len(vote_record['excused']) and \
           sane['absent'] == len(vote_record['absent']) and \
           sane['other'] == len(vote_record['other'])


class NMVoteScraper(Scraper):

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info(
                'no session specified, using latest session {}'.format(
                    session))

        chambers = [chamber] if chamber else ['upper', 'lower']

        for chamber in chambers:
            yield from self.scrape_vote(chamber, session)

    def scrape_vote(self, chamber, session):
        """ most document types (+ Votes) are in this common directory go
        through it and attach them to their related bills """
        session_path = session_slug(session)

        doc_path = 'http://www.nmlegis.gov/Sessions/{}/votes/'.format(
            session_path)

        self.info('Getting doc at {}'.format(doc_path))

        html = self.get(doc_path).text

        doc = lxml.html.fromstring(html)

        # all links but first one
        for fname in doc.xpath('//a/text()')[1:]:
            # if a COPY continue
            if re.search('- COPY', fname):
                continue

            # Delete any errant words found following the file name
            fname = fname.split(' ')[0]

            match = re.match(r'([A-Z]+)0*(\d{1,4})([^.]*)', fname.upper())
            if match == None:
                self.warning('No match, skipping')
                continue

            bill_type, bill_num, suffix = match.groups()

            # adapt to bill_id format
            bill_id = bill_type + ' ' + bill_num

            # votes
            if 'SVOTE' in suffix and chamber == 'upper':
                sv_text = self.scrape_vote_text(doc_path + fname)
                if not sv_text:
                    continue

                vote = self.parse_senate_vote(sv_text, doc_path + fname,
                                              session, bill_id)
                if not vote:
                    self.warning(
                        'Bad parse on the senate vote for {}'.format(bill_id))
                else:
                    yield vote

            elif 'HVOTE' in suffix and chamber == 'lower':
                hv_text = self.scrape_vote_text(doc_path + fname)
                if not hv_text:
                    continue
                vote = self.parse_house_vote(hv_text, doc_path + fname,
                                             session, bill_id)
                if not vote:
                    self.warning(
                        'Bad parse on the house vote for {}'.format(bill_id))
                else:
                    yield vote

    def scrape_vote_text(self, filelocation, local=False):
        """Retrieves or uses local copy of vote pdf and converts into XML."""
        if not local:
            try:
                filename, response = self.urlretrieve(url=filelocation)
                vote_text = convert_pdf(filename, type='xml')
                os.remove(filename)
            except scrapelib.HTTPError:
                self.warning('Request failed: {}'.format(filelocation))
                return
        else:
            vote_text = convert_pdf(filelocation, type='xml')
            os.remove(filelocation)
        return vote_text

    def parse_house_vote(self, hv_text, url, session, bill_id):
        """Sets any overrides and creates the vote instance"""
        overrides = {'ONEILL': "O'NEILL"}
        # Add new columns as they appear to be safe
        vote_record, row_headers, sane_row = self.parse_visual_grid(
            hv_text,
            overrides,
            h_vote_header,
            'CERTIFIED CORRECT',
            'YEAS')
        vote = build_vote(session, bill_id, url, vote_record, 'lower',
                          'house passage')

        try:
            validate_house_vote(row_headers, sane_row, vote_record)
        except ValueError:
            # This _should not be necessary_; fix ticketed out in
            # https://github.com/openstates/openstates/issues/2102
            self.warning("Found inconsistencies; throwing out individual votes, keeping totals")
            vote.votes = []
        return vote

    def parse_senate_vote(self, sv_text, url, session, bill_id):
        """Sets any overrides and creates the vote instance"""
        overrides = {'ONEILL': "O'NEILL"}
        # Add new columns as they appear to be safe
        vote_record, row_headers, sane_row = self.parse_visual_grid(
            sv_text,
            overrides,
            s_vote_header,
            'TOTAL',
            'TOTAL')
        vote = build_vote(session, bill_id, url, vote_record, 'upper', 'senate passage')

        validate_senate_vote(row_headers, sane_row, vote_record)
        return vote

    def parse_visual_grid(self, v_text, overrides, vote_header,
                          table_stop, sane_iden):
        """
        Takes a (badly)formatted pdf and converts the vote grid into an X,Y
        grid to match votes
        """
        vote_record = {
            'date': None,
            'yes': [],
            'no': [],
            'excused': [],
            'absent': [],
            'other': []
        }
        row_heads = {}
        column_map = {}
        rows = {}
        t_begin = 0
        t_stop = 0
        sane_row = 0
        # Take the mixed up text tag cells and separate header/special and
        # non-header cells.
        # Metadata hints that this doc is done by hand, tags appear in
        # chrono order not visual
        for tag in lxml.etree.XML(v_text).xpath('//text/b') + lxml.etree.XML(
                v_text).xpath('//text'):
            if tag.text is None:
                continue
            row_value = tag.text.strip()
            if 'top' not in tag.keys():
                tag = tag.getparent()
            top = int(tag.attrib['top'])
            # name overrides
            if row_value in overrides:
                row_value = overrides[row_value]
            elif 'LT. GOV' in row_value:
                # Special case for the senate, inconsistencies make overrides
                #  not an option
                row_value = 'LT. GOVERNOR'
            elif table_stop in row_value:
                # Set the data table end point
                t_stop = top

            if sane_iden in row_value:
                # Vote sanity row can be the same as the tableStop
                sane_row = top
            if date_regex.search(row_value):
                # Date formats change depending on what document is being used
                if len(row_value) == 8:
                    vote_record['date'] = datetime.strptime(
                        date_regex.search(row_value).group(), '%m/%d/%y')
                else:
                    vote_record['date'] = datetime.strptime(
                        date_regex.search(row_value).group(), '%m/%d/%Y')
            elif vote_header.match(row_value):
                row_heads[int(tag.attrib['left']) + int(
                    tag.attrib['width'])] = row_value
                # Set the header begin sanity value
                if t_begin == 0:
                    t_begin = top
            else:
                # Create dictionary of row params and x,y
                # location- y:{value, x, x(offset)}
                if top in rows:
                    rows[top].append((row_value, int(tag.attrib['left']),
                                      int(tag.attrib['width'])))
                else:
                    rows[top] = [(row_value, int(tag.attrib['left']),
                                  int(tag.attrib['width']))]

        # Mark the votes in the datagrid
        for row_x, cells in rows.items():
            if t_begin < row_x <= t_stop:
                # Resort the row cells to go left to right, due to possile
                # table pane switching
                cells.sort(key=operator.itemgetter(1))
                # Each vote grid is made up of split tables with two active
                # columns
                for x in range(0, len(cells), 2):
                    if table_stop in cells[x][0]:
                        break
                    if x + 1 >= len(cells):
                        self.warning('No vote found for {}'.format(cells[x]))
                        continue
                    if cells[x+1][1] not in column_map:
                        # Called one time for each column heading
                        # Map the data grid column to the header columns
                        column_map[cells[x+1][1]] = \
                            match_header(list(row_heads.keys()),
                                         cells[x + 1][1] + cells[x + 1][2])
                    vote_cast = row_heads[column_map[cells[x+1][1]]]

                    # Fix some odd encoding issues
                    name = correct_name(''.join(convert_sv_char(c) for c in
                                                cells[x][0]))
                    if 'Y' == vote_cast[0]:
                        vote_record['yes'].append(name)
                    elif 'N' == vote_cast[0]:
                        vote_record['no'].append(name)
                    elif 'E' == vote_cast[0]:
                        vote_record['excused'].append(name)
                    elif 'A' == vote_cast[0]:
                        vote_record['absent'].append(name)
                    else:
                        vote_record['other'].append(name)

        return vote_record, row_heads, rows[sane_row]
