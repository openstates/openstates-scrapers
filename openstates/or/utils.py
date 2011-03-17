def clean_space(str):
    new_str = ' '.join(str.split())
    return new_str

def base_url():
    return 'http://www.leg.state.or.us/'

def bills_url():
    return 'http://www.leg.state.or.us/bills_laws/billsinfo.htm'


def year_from_session(session):
    return int(session.split()[0])
