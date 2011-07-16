import urllib2
import contextlib

class ClosableString(str):
    def close(self):
        return self

def openFile(url):
    return contextlib.closing(ClosableString(urllib2.urlopen(url).read()))
