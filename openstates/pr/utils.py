import itertools

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 

def clean_newline(str):
        new_str = ' '.join(str.split('\n'))
        return new_str

def clean_space(str):
        new_str = ' '.join(str.split())
        return new_str
    
def between_keywords(key1, key2, str):
    right_part = str.split(key1)[0]
    return right_part.split(key2)[1]

def doc_link_url(doc_link_part):
    return 'http://www.camaraderepresentantes.org' + doc_link_part  

def committees_url(chamber):
    if chamber == 'upper':
        return {'permanent':'http://senadopr.us/Pages/ComisionesPermanentes.aspx',
                'special':'http://senadopr.us/Pages/ComisionesEspeciales.aspx',
                'joint':'http://senadopr.us/Pages/ComisionesConjuntas.aspx'}
    else:
        return {'permanent':'http://www.camaraderepresentantes.org/comisiones.asp',
                'special':'http://www.camaraderepresentantes.org/comisiones3.asp'}

def year_from_session(session):
    return int(session.split()[0])
