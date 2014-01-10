import logging
import datetime

from tater import Node, matches
from tater import Lexer, bygroups, include, Rule as r
from tater import Visitor


class HeaderLexer(Lexer):
    '''Lexer for the House PDF vote files that are normal (nice)
    PDFs with machine-readable text and no embedded images.
    '''
    # DEBUG = logging.DEBUG
    re_skip = r'[\s\n]+'
    dont_emit = ['Skip']

    tokendefs = {

        'root': [
            ('Skip', 'MASSACHUSETTS HOUSE OF REPRESENTATIVES'),
            include('meta'),
        ],

        'meta': [
            r('BillId', '[A-Z]\.\s{,2}\d+', push='motion'),
            (bygroups('Motion'), '(Shall.+?)\n\n'),
            ('Skip', 'Yea and Nay'),
            ('Date', r'[\d/]+ [\d:]+ [AP]M'),
            r(bygroups('CalendarNumber'), r'No. (\d+)',
              push=['votes', 'counts']),
        ],

        'motion': [
            (bygroups('Motion'), '(.+?)\n\n'),
        ],

        'counts': [
            (bygroups('YesCount'), r'(\d+)\s{,5}YEAS'),
            (bygroups('NoCount'), r'(\d+)\s{,5}NAYS'),
            (bygroups('OtherCount'), r'(\d+)\s{,5}N/V'),
        ],

        'votes': [
            (bygroups('Votes'), '(?s)(.+)\*=AFTER VOTE.+'),
        ]
    }


# ---------------------------------------------------------------
# Node definitions.
class Rollcall(Node):

    @matches('BillId')
    def handle_bill_id(self, *items):
        return self.descend('BillId', items)

    @matches('Motion')
    def handle_motion(self, *items):
        return self.descend('Motion', items)

    @matches('Date')
    def handle_date(self, *items):
        return self.descend('Date', items)

    @matches('CalendarNumber')
    def handle_calendar_number(self, *items):
        return self.descend('CalendarNumber', items)

    @matches('YesCount')
    def handle_yes_count(self, *items):
        return self.descend('YesCount', items)

    @matches('NoCount')
    def handle_no_count(self, *items):
        return self.descend('NoCount', items)

    @matches('OtherCount')
    def handle_other_count(self, *items):
        return self.descend('OtherCount', items)

    @matches('Votes')
    def handle_votes(self, *items):
        return self.descend('Votes', items)


# -----------------------------------------------------------------
# Visitor

class VoteVisitor(Visitor):

    def __init__(self):
        self.data = {}

    def visit_BillId(self, node):
        bill_id = node.first_text().replace('.', '')
        self.data['bill_id'] = bill_id

    def visit_Motion(self, node):
        self.data['motion'] = node.first_text()

    def visit_Date(self, node):
        fmt_string = '%m/%d/%y %S:%M %p'
        date = datetime.datetime.strptime(node.first_text(), fmt_string)
        self.data['date'] = date

    def visit_YesCount(self, node):
        self.data['yes_count'] = int(node.first_text())

    def visit_NoCount(self, node):
        self.data['no_count'] = int(node.first_text())

    def visit_OtherCount(self, node):
        self.data['other_count'] = int(node.first_text())

    def visit_Votes(self, node):
        self.data['votes'] = node.first_text()

    def finalize(self):
        return self.data
