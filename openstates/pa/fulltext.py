import re
import lxml.html

def collapse_spaces(text):
    return re.sub('\s+', ' ', text)

def extract_text(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # another state where the second column of the table is the good stuff
    text = ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
    return collapse_spaces(text)
