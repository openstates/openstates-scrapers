import logging
import datetime

from tater import Node, RegexLexer, bygroups, include, matches, parse
from tater import Visitor
from tater import Rule as r
from tater import Token as t


class HeaderLexer(RegexLexer):
    '''Lexer for the House PDF vote files that are normal (nice)
    PDFs with machine-readable text and no embedded images.
    '''
    # DEBUG = logging.DEBUG
    re_skip = r'[\s\n]+'
    dont_emit = [t.Skip]

    tokendefs = {

        'root': [
            r(t.Skip, 'MASSACHUSETTS HOUSE OF REPRESENTATIVES'),
            include('meta'),
        ],

        'meta': [
            r(t.BillId, '[A-Z]\.\s{,2}\d+', push='motion'),
            r(t.Skip, 'Yea and Nay'),
            r(t.Date, r'[\d/]+ [\d:]+ [AP]M'),
            r(bygroups(t.CalendarNumber), r'No. (\d+)',
              push=['votes', 'counts']),
        ],

        'motion': [
            r(bygroups(t.Motion), '(.+?)\n\n'),
        ],

        'counts': [
            r(bygroups(t.YesCount), r'(\d+)\s{,5}YEAS'),
            r(bygroups(t.NoCount), r'(\d+)\s{,5}NAYS'),
            r(bygroups(t.OtherCount), r'(\d+)\s{,5}N/V'),
        ],

        'votes': [
            r(bygroups(t.Votes), '(?s)(.+)\*=AFTER VOTE'),
        ]
    }


# ---------------------------------------------------------------
# Node definitions.
class Rollcall(Node):

    @matches(t.BillId)
    def handle_bill_id(self, *items):
        return self.descend(BillId, items)

    @matches(t.Motion)
    def handle_motion(self, *items):
        return self.descend(Motion, items)

    @matches(t.Date)
    def handle_date(self, *items):
        return self.descend(Date, items)

    @matches(t.CalendarNumber)
    def handle_calendar_number(self, *items):
        return self.descend(CalendarNumber, items)

    @matches(t.YesCount)
    def handle_yes_count(self, *items):
        return self.descend(YesCount, items)

    @matches(t.NoCount)
    def handle_no_count(self, *items):
        return self.descend(NoCount, items)

    @matches(t.OtherCount)
    def handle_other_count(self, *items):
        return self.descend(OtherCount, items)

    @matches(t.Votes)
    def handle_votes(self, *items):
        return self.descend(Votes, items)


class BillId(Node):
    pass


class Motion(Node):
    pass


class Date(Node):
    pass


class YesCount(Node):
    pass


class NoCount(Node):
    pass


class OtherCount(Node):
    pass


class Votes(Node):
    pass


class CalendarNumber(Node):
    pass


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
