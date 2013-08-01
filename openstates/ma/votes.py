# -*- coding: utf-8 -*-
import re
import pdb
import datetime
from operator import itemgetter

import sh
import tesseract

from tater import Node, RegexLexer, bygroups, include, matches, parse
from tater import Visitor
from tater import Rule as r
from tater import Token as t

from billy.utils import cd
from billy.scrape.utils import convert_pdf
from billy.scrape.votes import VoteScraper, Vote as BillyVote


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
        if chamber == 'upper':
            self.scrape_senate(session)
        elif chamber == 'lower':
            self.scrape_house(session)

    def scrape_senate(self, session):
        pass

    def scrape_house(self, session):
        n = 221
        while True:
            try:
                self.scrape_vote(session, n)
            except self.EndOfHouseVotes:
                break
            except self.MiscellaneousVote:
                pass
            n += 1

    def scrape_vote(self, session, rollcall_number):

        # if rollcall_number != 129:
        #     return

        # Fetch this piece of garbage.
        url = (
            'http://www.mass.gov/legis/journal/RollCallPdfs/'
            '{session}/{rollcall}.pdf?Session={session}&RollCall={rollcall}')
        url_args = dict(
            session=re.findall(r'\d+', session).pop(),
            rollcall=str(rollcall_number).zfill(5))
        url = url.format(**url_args)
        vote_file, resp = self.urlretrieve(url)
        text = convert_pdf(vote_file, type='text')
        text = text.decode('utf8')

        # A hack to guess whether this PDF has embedded images or contains
        # machien readable text.
        if len(re.findall(r'[YNPX]', text)) > 157:
            vote = self.house_get_vote(text, vote_file, session)
            self.house_add_votes(text, image_file, vote_file, vote)
        else:
            vote = self.house_get_vote_with_images(vote_file, session)
            self.house_add_votes_from_image(text, image_file, vote_file, vote)

        vote.add_source(url)
        self.house_check_vote(vote)
        self.save_vote(vote)

    def house_get_vote(self, text, vote_file, session):
        import pdb; pdb.set_trace()

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

    def house_add_votes(self, image_file, vote_file, vote):

        # Extract the image.
        with cd('/tmp'):
            sh.pdfimages(vote_file, vote_file)

        # Convert it to .png
        image_file = vote_file + '-000.pbm'
        try:
            sh.convert(image_file, image_file.replace('.pbm', '.png'))
        except sh.ErrorReturnCode_1:
            # This pdf had no images in it.
            raise self.MiscellaneousVote('PDF had no images in it.')

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

        tree = parse(Rollcall, Lexer(text))

        visitor = VoteVisitor(vote).visit(tree)

    def house_check_vote(self, vote):
        assert len(vote['yes_votes']) == vote['yes_count']
        assert len(vote['no_votes']) == vote['no_count']
        assert len(vote['other_votes']) == vote['other_count']

# ---------------------------------------------------------------------------
# Break the rollcall into tokens.
class Lexer(RegexLexer):

    re_skip = r'[\s\n]+'
    dont_emit = [t.Skip]

    re_name = r'[A-Z][a-z]+[A-Za-z]+'

    # import logging
    # DEBUG = logging.DEBUG
    tokendefs = {

        'root': [
            include('vote_value'),
        ],

        'vote_value': [
            # Tokenize vote values.
            r(bygroups(t.VoteVal), r'^([NYXP])', 'name'),
            r(bygroups(t.VoteVal), r'([NYXP])', 'name'),
        ],

        'name': [
            r(t.Skip, r'\*'),

            # Hypephenated last name.
            r(t.Name, r'%s\s*-\s*%s' % (re_name, re_name)),

            # Tokenize names, Smith
            r(t.Name, re_name),

            # Tokenize deMacedo
            r(t.Name, r'(de|di|da)%s' % re_name),

            # Special case of Mr. Speaker
            r(t.Speaker, 'Mrs?\s*\.\s+Speaker'),

            # O'Flanery, D'Emilia
            r(t.Name, "[OD]\s*\s*' %s" % re_name),

            # The comma after Smith ,
            r(t.Comma, r','),

            # The trailing initial of Smith , J .
            r(bygroups(t.Initial), '([A-Z])\s*\.'),

            # Lower case name fragments.
            r(t.Fragment, '[a-z]+'),
            ],
        }


# ---------------------------------------------------------------------------
# Node definitions for assembling the tokens into a tree.
class Rollcall(Node):

    @matches(t.VoteVal)
    def handle_vote(self, *items):
        return self.descend(Vote).descend(VoteValue, items)


class Vote(Node):

    @matches(t.Name)
    def handle_name(self, *items):
        return self.descend(Name, items)

    @matches(t.Speaker)
    def handle_speaker(self, *items):
        return self.descend(Speaker, items)


class VoteValue(Node):
    pass


class Name(Node):

    @matches(t.Comma, t.Initial)
    def handle_initial(self, *items):
        comma, initial = items
        return self.descend(Initial, initial)

    @matches(t.Fragment)
    def handle_fragment(self, *items):
        '''Append any lowercase name fragments to the main name.
        '''
        return self.extend(*items)


class Speaker(Node):
    '''Represent's the speaker's vote.
    '''

class Initial(Node):
    '''Represents a voter name's initial, like Smith *J .*
    '''

# ---------------------------------------------------------------------------
# Visit the parse tree and add votes from it.
class VoteVisitor(Visitor):

    def __init__(self, vote_object):
        self.vote = vote_object

    def visit_Vote(self, node):
        # Get vote value.
        vote_value = node.find_one('VoteValue').first_text()

        # Get voter name.
        if node.find_one('Speaker'):
            voter_name = node.find_one('Speaker').first_text()
            voter_name = voter_name.replace(' . ', '. ')
            initial = ''
        else:
            voter_name = map(itemgetter(2), node.find_one('Name').items)
            voter_name = ''.join(voter_name)
            voter_name = voter_name.replace(' ', '')
            initial = node.find_one('Initial')
            if initial is not None:
                initial = initial.first_text()
                voter_name += ', %s.' % initial

        # Add to the vote object.
        if vote_value == 'N':
            self.vote.no(voter_name)
        elif vote_value == 'Y':
            self.vote.yes(voter_name)
        if vote_value in 'XP':
            self.vote.other(voter_name)
