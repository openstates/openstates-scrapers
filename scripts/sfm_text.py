import re
import time
import argparse
import lxml.html

import gridfs

from billy.conf import settings, base_arg_parser
from billy.scrape.utils import convert_pdf
from billy.utils import configure_logging

from oyster.client import get_configured_client
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


def az_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    text = doc.xpath('//div[@class="Section2"]')[0].text_content()
    return collapse_spaces(text)

def wv_handler(filedata, metadata):
    doc = lxml.html.fromstring(filedata)
    return doc.xpath('//div[@id="blocktext"]')[0].text_content()


handlers = {
    #'ca': ca_handler,
    'ny': ny_handler,
    'fl': fl_handler,
    'pa': pa_handler,
    'oh': oh_handler,
    'mi': mi_handler,
    'nc': nc_handler,
    'nj': nj_handler,
    'ma': ma_handler,
    'va': va_handler,
    'az': az_handler,
    'wa': wa_handler,
    #'md': md_handler,
    'wv': wv_handler,
}


def process_state_files(state, server):
    oclient = get_configured_client()
    sfm_client = Client(server)

    new_versions = list(oclient.db.tracked.find({'metadata.state': state,
                                     'superfastmatch_id': {'$exists': False}}))
    extract_text = handlers[state]
    print '%s new versions to sync' % len(new_versions)

    for version in new_versions:
        _id = int(time.time()*10000)
        try:
            filedata = oclient.get_version(version['url']).read()
        except gridfs.errors.NoFile:
            continue
        metadata = version['metadata']
        text = extract_text(filedata, metadata)
        sfm_client.add(1, _id, text, defer=True,
               title='%(state)s %(session)s %(bill_id)s %(name)s' % metadata,
                **metadata)
    sfm_client.update_associations()

def main():
    parser = argparse.ArgumentParser(
        description='Convert state bills to SFM-ready text',
        parents=[base_arg_parser],
    )
    parser.add_argument('state', type=str, help='state')
    parser.add_argument('--sfm_server', type=str, help='URL of SFM instance',
                        default='http://localhost:8080/')

    args = parser.parse_args()

    settings.update(args)

    configure_logging(args.verbose, args.state)

    process_state_files(args.state, args.sfm_server)

if __name__ == '__main__':
    main()
