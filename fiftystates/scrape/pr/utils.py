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