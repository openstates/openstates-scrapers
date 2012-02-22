import re
import time
import lxml.html

from billy.scrape.utils import convert_pdf

from superfastmatch import Client

def collapse_spaces(text):
    return re.sub('\s+', ' ', text)

def text_after_line_numbers(lines):
    text = ''
    for line in lines:
        # real bill text starts with an optional space, line number
        # more spaces, then real text
        match = re.match('\s*\d+\s+(.*)', line)
        if match:
            text += match.groups()[0] + ' '
    # text winds up being all real bill text joined w/ spaces
    return text.decode('utf-8', 'ignore')

def az_handler(filedata):
    html = lxml.html.fromstring(filedata)
    text = html.xpath('//div[@class="Section2"]')[0].text_content()
    return collapse_spaces(text)

def ca_handler(filedata, metadata):
    if file.endswith('.pdf'):
        # NOTE: this strips the summary, it'd be useful for search (but not SFM)
        lines = convert_pdf(file, 'text').splitlines()
        return text_after_line_numbers(lines)
    elif file.endswith('.html'):
        doc = lxml.html.fromstring(open(file).read())
        text = doc.xpath('//pre')[0].text_content()
        return collapse_spaces(text)

def ny_handler(filedata, metadata):
    if filedata:
        doc = lxml.html.fromstring(filedata)
        text = doc.xpath('//pre')[0].text_content()
        # if there's a header above a _________, ditch it
        text = text.rsplit('__________', 1)[-1]
        # strip numbers from lines
        text = re.sub('\n\s*\d+\s*', ' ', text)
        text = collapse_spaces(text)
        return text
    else:
        return ''

def md_handler(filedata, metadata):
    lines = convert_pdf(file, 'text').splitlines()
    return text_after_line_numbers(lines)


def fl_handler(filedata, metadata):

    # check for beginning of tag, MS throws in some xmlns stuff
    if '<html' not in filedata:
        return ''

    doc = lxml.html.fromstring(filedata)
    if metadata['chamber'] == 'lower':
        # 2nd column of the table has all of the good stuff, first is line #
        return ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
    else:
        text = doc.xpath('//pre')[0].text_content()
        return text_after_line_numbers(text.splitlines())


def pa_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # another state where the second column of the table is the good stuff
    text = ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
    return collapse_spaces(text)


def oh_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # left-aligned columns
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@align="LEFT"]'))
    return collapse_spaces(text)


def mi_handler(filedata, metadata):
    # no real pattern here, just grab the text from the body
    doc = lxml.html.fromstring(filedata)
    return collapse_spaces(doc.xpath('//body')[0].text_content())


def nc_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    # all content has a class that starts with a (aSection, aTitle, etc)
    text = ' '.join([x.text_content() for x in
                     doc.xpath('//p[starts-with(@class, "a")]')])
    return collapse_spaces(text)


def nj_handler(filedata, metadata):
    if metadata['filename'].endswith('.WPD'):
        return ''
    else:
        doc = lxml.html.fromstring(filedata)
        text = doc.xpath('//div[@class="Section3"]')[0].text_content()
        return collapse_spaces(text)


def va_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    text = ' '.join(x.text_content()
                    for x in doc.xpath('//div[@id="mainC"]/p'))
    return collapse_spaces(text)


def wa_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    text = '\n'.join(collapse_spaces(x.text_content()) for x in
                     doc.xpath('//body/p'))
    return text


def ma_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    return ' '.join([x.text_content()
                     for x in doc.xpath('//td[@class="longTextContent"]//p')])



def wv_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    return doc.xpath('//div[@id="blocktext"]')[0].text_content()


handlers = {
    'az': az_handler,
}


def push_to_sfm(doc, newdata):
    server = 'http://ec2-23-20-68-251.compute-1.amazonaws.com/'
    sfm_client = Client(server)

    metadata = doc['metadata']
    state = metadata['state']
    extractor = handlers[state]
    text = extractor(newdata)

    _id = time.time()*1000000

    sfm_client.add(1, _id, text, defer=True,
                   title='%(state)s %(session)s %(bill_id)s %(name)s' % metadata,
                   **metadata)
