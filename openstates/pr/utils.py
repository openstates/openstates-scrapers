import itertools

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 

def clean_newline(str):
        new_str = ' '.join(str.split('\n'))
        return new_str

def between_keywords(key1, key2, str):
    right_part = str.split(key1)[0]
    return right_part.split(key2)[1]

def doc_link_url(doc_link_part):
    return 'http://www.camaraderepresentantes.org' + doc_link_part  


def year_from_session(session):
    return int(session.split()[0])
