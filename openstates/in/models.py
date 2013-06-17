import re
import os
import datetime
import collections

from billy.scrape.utils import convert_pdf, PlaintextColumns
from billy.scrape.votes import Vote


class PDFHouseVote(object):

    class VoteParseError(Exception):
        pass

    def __init__(self, url, scraper):
        self.url = url
        self.scraper = scraper

    @property
    def text(self):
        text = getattr(self, '_text', None)
        if text:
            return text
        (path, resp) = self.scraper.urlretrieve(self.url)
        text = convert_pdf(path, 'text')
        os.remove(path)
        self._text = text
        return text

    def date(self):
        try:
            date = re.search(r'\d\d-\d\d-\d\d', self.text).group(0)
        except AttributeError:
            msg = "Couldn't find date on %s" % self.url
            self.scraper.logger.warning(msg)
            raise self.VoteParseError(msg)
        return datetime.datetime.strptime(date, "%m-%d-%y")

    def _parse_vote_count(s):
        if s == 'NONE':
            return 0
        return int(s)

    def _parse(self):
        counts_map = {'VOTING YEA': 'yes',
                      'VOTING NAY': 'no'}
        counts = []
        boundaries = []
        boundary_keys = []
        bail = False
        for matchobj in re.finditer(r'(.*?VOTING.*?):.+?(\w+)', self.text):
            boundary_key = vote_val, count = matchobj.groups()
            boundary_keys.append(boundary_key)
            try:
                count = int(count)
            except ValueError:
                bail = True
            counts.append((counts_map.get(vote_val, 'other'), count))
            if boundaries:
                boundaries.append(matchobj.start())
            if bail:
                break
            boundaries.append(matchobj.end())

        # Get a list of spans.
        spans = []
        while True:
            span = []
            try:
                span.append(boundaries.pop(0))
                span.append(boundaries.pop(0))
                spans.append(span)
            except IndexError:
                # if span:
                #     span.append(None)
                #     spans.append(span)
                break

        # Yield the vote type,
        for count, key, span in zip(counts, boundary_keys, spans):
            yield count, key, self.text[slice(*span)]

    def motion(self):
        motion_line = None
        lines = self.text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('MEETING DAY'):
                motion_line = i + 7
        motion = re.split(r'\s{2,}', lines[motion_line].strip())[0].strip()
        if not motion:
            msg = "Couldn't find motion for %s" % self.url
            self.scraper.logger.warning(msg)
            raise self.VoteParseError(msg)
        return motion

    def passed(self):

        result_types = {
            'FAILED': False,
            'DEFEATED': False,
            'PREVAILED': True,
            'PASSED': True,
            'SUSTAINED': True,
            'NOT SECONDED': False,
            'OVERRIDDEN': True,
        }
        rgx = r'Roll\s+Call\s+\d+:\s+(%s)' % '|'.join(result_types.keys())
        passed = re.search(rgx, self.text).group(1)
        passed = result_types[passed]
        return passed

    def vote(self):
        '''Return a billy vote.
        '''
        actual_vote_dict = collections.defaultdict(list)
        vote = Vote('lower', self.date(), self.motion(),
                    self.passed(), 0, 0, 0,
                    actual_vote=dict(actual_vote_dict))

        for (vote_val, count), (actual_vote, _), text in self._parse():
            vote[vote_val + '_count'] = count
            for name in filter(None, PlaintextColumns(text)):
                names = [name]
                if 'Candelaria Reardon' in name:
                    names.append('Candelaria Reardon')
                    other_name = name.replace('Candelaria Reardon', '').strip()
                    names.append(other_name)
                for name in filter(None, names):
                    actual_vote_dict[actual_vote].append(name)
                    getattr(vote, vote_val)(name)

        vote.add_source(self.url)
        return vote

