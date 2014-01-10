'''Lexer/parser classes for PDF vote files in which the roll call
votes are shown as embedded images.
'''
import logging
from operator import attrgetter

from tater import Lexer, bygroups, include
from tater import Node, matches
from tater import Visitor


class Lexer(Lexer):

    re_skip = r'[\s\n]+'
    dont_emit = ['Skip']

    re_name = r'[A-Z][a-z]+[A-Za-z]+'

    # DEBUG = logging.DEBUG
    tokendefs = {

        'root': [
            include('vote_value'),
        ],

        'vote_value': [
            # Tokenize vote values.
            (bygroups('VoteVal'), r'^([NYXP])', 'name'),
            (bygroups('VoteVal'), r'([NYXP])', 'name'),
        ],

        'name': [
            ('Skip', r'\*'),

            # Hypephenated last name.
            ('Name', r'%s\s*-\s*%s' % (re_name, re_name)),

            # Tokenize names, Smith
            ('Name', re_name),

            # Tokenize deMacedo
            ('Name', r'(de|di|da)%s' % re_name),

            # Special case of Mr. Speaker
            ('Speaker', 'Mrs?\s*\.\s+Speaker'),

            # O'Flanery, D'Emilia
            ('Name', "[OD]\s*'\s*[A-Z][a-z]+"),

            # The comma after Smith ,
            ('Comma', r','),

            # The trailing initial of Smith , J .
            (bygroups('Initial'), '([A-Z])\s*\.'),

            # Lower case name fragments.
            ('Fragment', '[a-z]+'),
            ],
        }


# ---------------------------------------------------------------------------
# Node definitions for assembling the tokens into a tree.
class Rollcall(Node):

    @matches('VoteVal')
    def handle_vote(self, *items):
        return self.descend(Vote).descend('VoteValue', items)


class Vote(Node):

    @matches('Name')
    def handle_name(self, *items):
        return self.descend('Name', items)

    @matches('Speaker')
    def handle_speaker(self, *items):
        return self.descend('Speaker', items)


class Name(Node):

    @matches('Comma', 'Initial')
    def handle_initial(self, *items):
        comma, initial = items
        return self.descend('Initial', initial)

    @matches('Fragment')
    def handle_fragment(self, *items):
        '''Append any lowercase name fragments to the main name.
        '''
        return self.extend(*items)


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
            voter_name = map(attrgetter('text'), node.find_one('Name').items)
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

