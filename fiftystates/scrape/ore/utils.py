def clean_space(str):
    new_str = ' '.join(str.split())
    return new_str

def base_url():
    return 'http://www.leg.state.or.us/'

def bills_url():
    return base_url() + 'bills_laws/billsinfo.htm'

def chambers_url(url_piece):
    return base_url() + url_piece + '/' + url_piece + '.csv'

def legs_url(url_piece):
    return base_url() + 'servlet/XSLT?URL=members.xml&xslURL=members.xsl&member-type=' + url_piece

def year_from_session(session):
    return int(session.split()[0])