import itertools

def base_url():
    return "http://www.capitol.hawaii.gov"

def versions_page_url(type, bill_number):
    return base_url() + '/session2009/getstatus.asp?query=' \
                         + type + bill_number + '&showtext=on&currpage=1'

def year_from_session(session):
    return int(session.split()[0].split('-')[0])

def legs_url(chamber):
    if chamber == 'upper':
        return base_url() + "/site1/info/direct/sendir.asp"
    else: 
        return base_url() + "/site1/info/direct/repdir.asp"

def bills_url(chamber):
    if chamber == "upper":
            return (base_url() + "/session2009/lists/RptIntroSB.aspx", "HB")
    else:
            return (base_url() + "/session2009/lists/RptIntroSB.aspx", "SB")
        
def bill_url(link):
    return base_url() + "/session2009/lists/" + link

def bill_version_url(link):
    return "http://www.capitol.hawaii.gov/session2009/Bills/" + link

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 
