# -*- coding: utf8 -*-
from datetime import datetime
import re
import collections

import lxml.etree

from billy.scrape.utils import convert_pdf
from billy.scrape.votes import VoteScraper, Vote


class IAVoteScraper(VoteScraper):
    state = 'ia'

    def scrape(self, chamber, session):

        getattr(self, 'scrape_%s' % chamber)(session)

    def scrape_lower(self, session):
        url = 'https://www.legis.iowa.gov/Legislation/journalIndex_House.aspx'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        urls = doc.xpath('//a[contains(@href, "DOCS")]/@href')[::-1]
        for url in urls:
            _, filename = url.rsplit('/', 1)
            try:
                date = datetime.strptime(filename, '%m-%d-%Y.pdf')
            except ValueError:
                msg = "%s doesn't smell like a date. Skipping."
                self.logger.info(msg % filename)
            self.scrape_journal(url, 'lower', session, date)

    def scrape_upper(self, session):
        url = 'https://www.legis.iowa.gov/Legislation/journalIndex_Senate.aspx'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        urls = doc.xpath('//a[contains(@href, "DOCS")]/@href')[::-1]
        for url in urls:
            _, filename = url.rsplit('/', 1)
            try:
                date = datetime.strptime(filename, '%m-%d-%Y.pdf')
            except ValueError:
                msg = "%s doesn't smell like a date. Skipping."
                self.logger.info(msg % filename)
            self.scrape_journal(url, 'upper', session, date)

    def _journal_lines(self, etree):
        '''A generator of text lines. Skip crap.
        '''
        for page in etree:
            for text in page.xpath('text')[3:]:
                yield text

    def scrape_journal(self, url, chamber, session, date):

        filename, response = self.urlretrieve(url)
        self.logger.info('Saved journal to %r' % filename)
        xml = convert_pdf(filename)
        try:
            et = lxml.etree.fromstring(xml)
        except lxml.etree.XMLSyntaxError:
            self.logger.warning('Skipping invalid pdf: %r' % filename)
            return

        lines = self._journal_lines(et)
        while True:
            try:
                line = next(lines)
            except StopIteration:
                break

            text = gettext(line)

            # Go through with vote parse if any of
            # these conditions match.
            if 'Shall' in text:
                if 'bill pass?' in text:
                    pass
                elif 'resolution' in text:
                    pass
                elif 'amendment' in text:
                    pass
                else:
                    continue
            else:
                continue

            # Get the bill_id.
            while True:
                line = next(lines)
                text += gettext(line)
                m = re.search(r'\(\s*([A-Z\.]+\s+\d+)\s*\)',  text)
                if m:
                    bill_id = m.group(1)
                    break

            motion = text.strip()
            motion = re.sub(r'\s+', ' ', motion)
            motion, _ = motion.rsplit('(')
            motion = motion.replace('"', '')
            motion = motion.replace(u'“', '')
            motion = motion.replace(u'\u201d', '')
            motion = motion.replace(u' ,', ',')
            motion = motion.strip()
            motion = re.sub(r'[SH].\d+', lambda m: ' %s ' % m.group(), motion)
            motion = re.sub(r'On the question\s*', '', motion, flags=re.I)

            for word, letter in (('Senate', 'S'),
                                 ('House', 'H'),
                                 ('File', 'F')):
                bill_id = bill_id.replace(word, letter)

            bill_chamber = dict(h='lower', s='upper')[bill_id.lower()[0]]
            self.current_id = bill_id
            votes = self.parse_votes(lines)
            totals = filter(lambda x: isinstance(x, int), votes.values())
            passed = (1.0 * votes['yes_count'] / sum(totals)) >= 0.5
            vote = Vote(motion=motion,
                        passed=passed,
                        chamber=chamber, date=date,
                        session=session, bill_id=bill_id,
                        bill_chamber=bill_chamber,
                        **votes)
            vote.update(votes)
            vote.add_source(url)
            self.save_vote(vote)

    def parse_votes(self, lines):

        counts = collections.defaultdict(list)
        DONE = 1
        boundaries = [

            # Senate journal.
            ('Yeas', 'yes'),
            ('Nays', 'no'),
            ('Absent', 'other'),
            ('Present', 'skip'),
            ('Amendment', DONE),
            ('Resolution', DONE),
            ('Bill', DONE),

            # House journal.
            ('The ayes were', 'yes'),
            ('The yeas were', 'yes'),
            ('The nays were', 'no'),
            ('Absent or not voting', 'other'),
            ('The bill', DONE),
            ('The committee', DONE),
            ('The resolution', DONE),
            ('The motion', DONE),
            ('The joint resolution', DONE),
            ('Under the', DONE)]

        def is_boundary(text, patterns={}):
            for blurb, key in boundaries:
                if text.strip().startswith(blurb):
                    return key

        while True:
            line = next(lines)
            text = gettext(line)
            if is_boundary(text):
                break

        while True:
            key = is_boundary(text)
            if key is DONE:
                break

            # Get the vote count.
            m = re.search(r'\d+', text)
            if not m:
                if 'none' in text:
                    votecount = 0
            else:
                votecount = int(m.group())
            if key != 'skip':
                counts['%s_count' % key] = votecount

            # Get the voter names.
            while True:
                line = next(lines)
                text = gettext(line)
                if is_boundary(text):
                    break
                elif not text.strip() or text.strip().isdigit():
                    continue
                else:
                    for name in self.split_names(text):
                        counts['%s_votes' % key].append(name.strip())

        return counts

    def split_names(self, text):
        junk = ['Presiding', 'Mr. Speaker', 'Spkr.', '.']
        text = text.strip()
        chunks = text.split()[::-1]
        name = [chunks.pop()]
        names = []
        while chunks:
            chunk = chunks.pop()
            if len(chunk) < 3:
                name.append(chunk)
            elif name[-1] in ('Mr.', 'Van', 'De', 'Vander'):
                name.append(chunk)
            else:
                name = ' '.join(name).strip(',')
                if name and (name not in names) and (name not in junk):
                    names.append(name)

                # Seed the next loop.
                name = [chunk]

        # Similar changes to the final name in the sequence.
        name = ' '.join(name).strip(',')
        if names and len(name) < 3:
            names[-1] += ' %s' % name
        elif name and (name not in names) and (name not in junk):
            names.append(name)
        return names


def _get_chunks(el, buff=None, until=None):
    tagmap = {'br': '\n'}
    buff = buff or []

    # Tag, text, tail, recur...
    yield tagmap.get(el.tag, '')
    yield el.text or ''
    if el.text == 'until':
        return
    for kid in el:
        for text in _get_chunks(kid, until=until):
            yield text
            if text == until:
                return
    if el.tail:
        yield el.tail
        if el.tail == until:
            return
    if el.tag == 'text':
        yield '\n'


def gettext(el):
    '''Join the chunks, then split and rejoin to normalize the whitespace.
    '''
    return ' '.join(''.join(_get_chunks(el)).split())
