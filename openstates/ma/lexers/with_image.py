'''Lexer/parser classes for PDF vote files in which the roll call
votes are shown as embedded images.
'''
import logging
from operator import itemgetter

from tater import Node, RegexLexer, bygroups, include, matches, parse
from tater import Visitor
from tater import Rule as r
from tater import Token as t


class Lexer(RegexLexer):

    re_skip = r'[\s\n]+'
    dont_emit = [t.Skip]

    re_name = r'[A-Z][a-z]+[A-Za-z]+'

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
            r(t.Name, "[OD]\s*'\s*[A-Z][a-z]+"),

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

