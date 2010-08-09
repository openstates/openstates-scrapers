import itertools

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 

def bills_url(year):
    return 'http://www.leg.state.co.us/CLICS/CLICS' + str(year) + 'A/csl.nsf/%28bf-1%29?OpenView&Count=2000'

def leg_form_url():
    return 'http://www.leg.state.co.us//clics/clics2010a/directory.nsf/d1325833be2cc8ec0725664900682205?SearchView'

def legs_url(chamber):
    url = 'http://www.leg.state.co.us/Clics/CLICS2010A/directory.nsf/MIWeb?OpenForm&chamber='
    if chamber == 'upper':
        return url + 'Senate'
    else:
        return url + 'House'

def party_name(party_letter):
    if party_letter == 'D':
        return 'Republican'
    elif party_letter == 'R':
        return 'Democrat'
    else:
        return 'Independent'

def year_from_session(session):
    return int(session.split()[0])

def base_url():
    return 'http://www.leg.state.co.us'
