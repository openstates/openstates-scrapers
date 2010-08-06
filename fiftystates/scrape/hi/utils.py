import itertools

def versions_page(type, bill_number):
    return 'http://www.capitol.hawaii.gov/session2009/getstatus.asp?query=' \
                         + type + bill_number + '&showtext=on&currpage=1'

def year_from_session(session):
    return int(session.split()[0])

def legs_url(chamber):
    if chamber == 'upper':
        return "http://www.capitol.hawaii.gov/site1/info/direct/sendir.asp"
    else: 
        return "http://www.capitol.hawaii.gov/site1/info/direct/repdir.asp"

def bills_url(chamber):
    if chamber == "upper":
            return ("http://www.capitol.hawaii.gov/session2009/lists/RptIntroSB.aspx", "HB")
    else:
            return ("http://www.capitol.hawaii.gov/session2009/lists/RptIntroSB.aspx", "SB")

# From the itertools docs's recipe section 
def grouper(self, n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 
