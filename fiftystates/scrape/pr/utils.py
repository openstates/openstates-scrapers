import lxml.html
import contextlib

@contextlib.contextmanager
def lxml_context(self, url):
    try:
        body = self.urlopen(url)
    except:
        body = self.urlopen("http://www.google.com") 
    
    elem = lxml.html.fromstring(body)
    
    try:
        yield elem
    except:
        print "FAIL"
        #self.show_error(url, body)
        raise

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