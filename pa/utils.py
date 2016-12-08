import datetime


def bill_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def start_year(session):
    return session[0:4]


def parse_action_date(date_str):
    date_str = date_str.replace('Sept.', 'September')
    try:
        date = datetime.datetime.strptime(date_str, '%b. %d, %Y')
    except ValueError:
        date = datetime.datetime.strptime(date_str, '%B %d, %Y')
    return date


def bill_list_url(chamber, session, special):
    return 'http://www.legis.state.pa.us/cfdocs/legis/bi/'\
        'BillIndx.cfm?sYear=%s&sIndex=%i&bod=%s' % (
        start_year(session), special, bill_abbr(chamber))


def history_url(chamber, session, special, type, bill_number):
    return 'http://www.legis.state.pa.us/cfdocs/billinfo/'\
        'bill_history.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s' % (
        start_year(session), special, bill_abbr(chamber), type, bill_number)


def info_url(chamber, session, special, type, bill_number):
    return 'http://www.legis.state.pa.us/cfdocs/billinfo/'\
        'billinfo.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s' % (
        start_year(session), special, bill_abbr(chamber), type, bill_number)


def vote_url(chamber, session, special, type, bill_number):
    return 'http://www.legis.state.pa.us/cfdocs/billinfo/'\
        'bill_votes.cfm?syear=%s&sind=%d&body=%s&type=%s&bn=%s' % (
        start_year(session), special, bill_abbr(chamber), type, bill_number)


def legislators_url(chamber):
    if chamber == 'upper':
        return "http://www.legis.state.pa.us/cfdocs/legis/home/"\
            "member_information/senators_alpha.cfm"
    else:
        return "http://www.legis.state.pa.us/cfdocs/legis/home/"\
            "member_information/representatives_alpha.cfm"
