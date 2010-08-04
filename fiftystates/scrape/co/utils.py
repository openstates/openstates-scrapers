import itertools

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 

def bills_url(year):
    return "http://www.leg.state.co.us/CLICS/CLICS" + str(year) + "A/csl.nsf/%28bf-1%29?OpenView&Count=2000"