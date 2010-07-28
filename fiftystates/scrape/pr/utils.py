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

def legislators_url(chamber):
    if 'upper':
        return ('http://www.senadopr.us/senadores/Pages/Senadores%20Acumulacion.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20I.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20II.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20III.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20IV.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20V.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VI.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VII.aspx',
                                'http://www.senadopr.us/Pages/Senadores%20Distrito%20VIII.aspx')
    else:
        return 'http://www.camaraderepresentantes.org/legsv.asp'

def committees_url(chamber):
    if chamber == 'upper':
        return {'permanent':'http://senadopr.us/Pages/ComisionesPermanentes.aspx',
                'special':'http://senadopr.us/Pages/ComisionesEspeciales.aspx',
                'joint':'http://senadopr.us/Pages/ComisionesConjuntas.aspx'}
    else:
        return {'permanent':'http://www.camaraderepresentantes.org/comisiones.asp',
                'special':'http://www.camaraderepresentantes.org/comisiones3.asp'}