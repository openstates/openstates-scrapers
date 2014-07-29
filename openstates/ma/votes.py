# -*- coding: utf-8 -*-
import re
import os
import pdb
import datetime
from operator import itemgetter
import contextlib

import sh
import tesseract

import scrapelib
from billy.scrape.utils import convert_pdf
from billy.scrape.votes import VoteScraper, Vote as BillyVote

from .lexers import with_image
from .lexers import without_image


@contextlib.contextmanager
def cd(path):
    '''Creates the path if it doesn't exist'''
    old_dir = os.getcwd()
    try:
        os.makedirs(path)
    except OSError:
        pass
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


class MAVoteScraper(VoteScraper):
    jurisdiction = 'ma'

    class EndOfHouseVotes(Exception):
        '''Raise when there are no more house votes to scrape.
        '''
        pass

    class MiscellaneousVote(Exception):
        '''Sometimes the chamber will vote on something that isn't
        related to a bill, like whether to suspend the rules in order
        to continue to meet late in the night.
        See http://www.mass.gov/legis/journal/RollCallPdfs/188/00060.pdf?Session=188&RollCall=00060
        '''

    def scrape(self, chamber, session):
        self.filenames = []
        if chamber == 'upper':
            self.scrape_senate(session)
        elif chamber == 'lower':
            self.scrape_house(session)

    def scrape_senate(self, session):
        pass

    def scrape_house(self, session):
        n = 1
        while True:
            try:
                self.scrape_vote(session, n)
            except self.EndOfHouseVotes:
                break
            except self.MiscellaneousVote:
                pass
            n += 1

    def scrape_vote(self, session, rollcall_number):

        # Fetch this piece of garbage.
        url = (
            'http://www.mass.gov/legis/journal/RollCallPdfs/'
            '{session}/{rollcall}.pdf?Session={session}&RollCall={rollcall}')
        url_args = dict(
            session=re.findall(r'\d+', session).pop(),
            rollcall=str(rollcall_number).zfill(5))
        url = url.format(**url_args)

        try:
            vote_file, resp = self.urlretrieve(url)
        except scrapelib.HTTPError:
            # We'll hit a 404 at the end of the votes.
            self.warning('Stopping; encountered a 404 at %s' % url)
            raise self.EndOfHouseVotes

        text = convert_pdf(vote_file, type='text')
        text = text.decode('utf8')

        # A hack to guess whether this PDF has embedded images or contains
        # machine readable text.
        if len(re.findall(r'[YNPX]', text)) > 157:
            vote = self.house_get_vote(text, vote_file, session)
        else:
            vote = self.house_get_vote_with_images(text, vote_file, session)
            self.house_add_votes_from_image(vote_file, vote)

        vote.add_source(url)
        if not self.house_check_vote(vote):
            self.logger.warning('Bad vote counts for %s' % vote)
            return
        self.save_vote(vote)
        os.remove(vote_file)

    def house_get_vote(self, text, vote_file, session):

        # Skip quorum votes.*
        if 'QUORUM' in text:
            raise self.MiscellaneousVote

        # Parse the text into a tree.
        tree = without_image.Rollcall.parse(without_image.HeaderLexer(text))

        # Visit the tree and add rollcall votes to the vote object.
        vote_data = without_image.VoteVisitor().visit(tree)

        if 'bill_id' not in vote_data:
            msg = 'Skipping vote not associated with any bill_id'
            self.logger.warning(msg)
            raise self.MiscellaneousVote(msg)

        vote_data['passed'] = vote_data['yes_count'] > vote_data['no_count']
        vote_data['session'] = session
        vote_data['bill_chamber'] = {
            'S': 'upper',
            'H': 'lower'}[vote_data['bill_id'][0]]

        voters = vote_data.pop('votes')
        vote = BillyVote('lower', **vote_data)

        # Parse the text into a tree.
        tree = with_image.Rollcall.parse(with_image.Lexer(voters))

        # Visit the tree and add rollcall votes to the vote object.
        visitor = with_image.VoteVisitor(vote).visit(tree)

        return vote

    def house_get_vote_with_images(self, text, vote_file, session):
        _, motion_start = re.search('Yea and Nay No.+', text).span()
        motion_end, _ = re.search('YEAS', text).span()
        motion = text[motion_start:motion_end]
        motion = ' '.join(motion.strip().split())

        counts_re = r'([A-Z\-]+):\s+(\d+)'
        counts = dict(re.findall(counts_re, text))

        date = re.search(r'\S+ \d+, \d{4}', text).group()
        date = datetime.datetime.strptime(date, '%B %d, %Y')

        chamber_re = r'(Senate|House),\s+No\. (\d+)'
        bill_chamber = re.search(chamber_re, text)
        if bill_chamber is None:
            raise self.MiscellaneousVote('Vote not realted to a bill.')
        chamber, bill_id = bill_chamber.groups()
        bill_chamber = {
            'Senate': 'upper',
            'House': 'lower'}[chamber]

        if bill_chamber == 'lower':
            bill_id = 'H ' + bill_id
        else:
            bill_id = 'S ' + bill_id

        yes = int(counts['YEAS'])
        no = int(counts['NAYS'])
        other = int(counts.get('N-V', 0))

        vote = BillyVote('lower', date, motion, (yes > no),
                    yes, no, other, session=session, bill_id=bill_id,
                    bill_chamber=bill_chamber)

        return vote

    def house_add_votes_from_image(self, vote_file, vote):

        # Extract the image.
        with cd('/tmp'):
            sh.pdfimages(vote_file, vote_file)

        # Convert it to .png
        image_file = vote_file + '-000.pbm'

        with open(image_file, 'rb') as f:
            data = f.read()
            api = tesseract.TessBaseAPI()
            api.Init(".", "eng", tesseract.OEM_DEFAULT)
            api.SetPageSegMode(tesseract.PSM_SINGLE_BLOCK)
            whitelist = (
                "abcdefghijklmnopqrstuvwxyz',-.*"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
            api.SetVariable("tessedit_char_whitelist", whitelist)
            text = tesseract.ProcessPagesBuffer(data, len(data), api)

        # Parse the text into a tree.
        tree = with_image.Rollcall.parse(with_image.Lexer(text))

        # Visit the tree and add rollcall votes to the vote object.
        visitor = with_image.VoteVisitor(vote).visit(tree)

        os.remove(image_file)

    def house_check_vote(self, vote):
        return all([
            len(vote['yes_votes']) == vote['yes_count'],
            len(vote['no_votes']) == vote['no_count'],
            len(vote['other_votes']) == vote['other_count']])
